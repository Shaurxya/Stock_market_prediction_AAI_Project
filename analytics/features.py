"""Matching Spark and pandas workloads. All windows end at the current session."""
from .common import KEYS

METRICS = ['daily_return', 'sma_20', 'sma_50', 'volatility_20', 'volume_ratio']


def spark_features(clean, anomaly_threshold=2.0):
    from pyspark.sql import functions as F, Window
    # Observed exchange sessions: union of all accepted symbols, never fabricated days.
    calendar = clean.select('market', 'exchange', 'date').distinct().withColumn(
        '_session', F.dense_rank().over(Window.partitionBy('market', 'exchange').orderBy('date')))
    data = clean.join(calendar, ['market', 'exchange', 'date'])
    order = Window.partitionBy(*KEYS).orderBy('date')
    w20, w50, prior20 = order.rowsBetween(-19, 0), order.rowsBetween(-49, 0), order.rowsBetween(-20, -1)
    data = (data.withColumn('previous_date', F.lag('date').over(order))
            .withColumn('_previous_adj', F.lag('adj_close').over(order))
            .withColumn('_previous_session', F.lag('_session').over(order))
            .withColumn('gap_sessions', F.when(F.col('_previous_session').isNotNull(),
                         F.col('_session') - F.col('_previous_session') - 1))
            .withColumn('calendar_gap_days', F.datediff('date', 'previous_date')))
    continuous = ((F.col('gap_sessions') == 0) & (F.col('calendar_gap_days') <= 7))
    data = data.withColumn('daily_return', F.when(continuous & (F.col('_previous_adj') > 0),
                           F.col('adj_close') / F.col('_previous_adj') - 1))
    for name, window, column, expression, size in [
        ('sma_20', w20, 'adj_close', F.avg('adj_close'), 20),
        ('sma_50', w50, 'adj_close', F.avg('adj_close'), 50),
        ('volatility_20', w20, 'daily_return', F.stddev_samp('daily_return'), 20),
        ('_volume_baseline', prior20, 'volume', F.avg('volume'), 20),
    ]:
        data = data.withColumn(name, F.when(F.count(column).over(window) == size, expression.over(window)))
    return (data.withColumn('volume_ratio', F.when(F.col('_volume_baseline') > 0,
                             F.col('volume') / F.col('_volume_baseline')))
            .withColumn('volume_anomaly', F.col('volume_ratio') >= anomaly_threshold)
            .drop('_session', '_previous_session', '_previous_adj', '_volume_baseline'))


def pandas_features(clean, anomaly_threshold=2.0):
    import numpy as np
    import pandas as pd
    data = clean.copy()
    data['date'] = pd.to_datetime(data['date'])
    calendar = data[['market', 'exchange', 'date']].drop_duplicates().sort_values(['market', 'exchange', 'date'])
    calendar['_session'] = calendar.groupby(['market', 'exchange']).cumcount()
    data = data.merge(calendar).sort_values(KEYS + ['date']).reset_index(drop=True)
    groups = data.groupby(KEYS, sort=False)
    data['previous_date'] = groups['date'].shift()
    data['gap_sessions'] = groups['_session'].diff() - 1
    data['calendar_gap_days'] = (data['date'] - data['previous_date']).dt.days
    previous = groups['adj_close'].shift()
    data['daily_return'] = (data['adj_close'] / previous - 1).where(
        (data['gap_sessions'] == 0) & (data['calendar_gap_days'] <= 7) & (previous > 0))
    groups = data.groupby(KEYS, sort=False)
    for window in (20, 50):
        data[f'sma_{window}'] = groups['adj_close'].transform(lambda x: x.rolling(window).mean())
    data['volatility_20'] = groups['daily_return'].transform(lambda x: x.rolling(20).std(ddof=1))
    baseline = groups['volume'].transform(lambda x: x.shift().rolling(20).mean())
    data['volume_ratio'] = (data['volume'] / baseline).where(baseline > 0)
    data['volume_anomaly'] = data['volume_ratio'].ge(anomaly_threshold).where(data['volume_ratio'].notna(), None)
    return data.drop(columns=['_session']).replace([np.inf, -np.inf], np.nan)


def spark_aggregates(features):
    from pyspark.sql import functions as F, Window
    group = ['market', 'currency', 'date']
    result = features.groupBy(*group).agg(
        F.count('*').alias('stocks'), F.avg('daily_return').alias('mean_return'),
        F.sum(F.when(F.col('daily_return') > 0, 1).otherwise(0)).alias('advancing'),
        F.sum(F.when(F.col('daily_return') < 0, 1).otherwise(0)).alias('declining'),
        F.sum(F.when(F.col('daily_return') == 0, 1).otherwise(0)).alias('unchanged'))
    rankings = features.filter(F.col('daily_return').isNotNull()).withColumn(
        'rank', F.row_number().over(Window.partitionBy(*group).orderBy(F.desc('daily_return'), *KEYS)))
    return result, rankings.filter('rank <= 10')


def pandas_aggregates(features):
    group = ['market', 'currency', 'date']
    data = features.assign(advancing=(features.daily_return > 0).astype(int),
                           declining=(features.daily_return < 0).astype(int),
                           unchanged=(features.daily_return == 0).astype(int))
    aggregates = data.groupby(group).agg(stocks=('ticker', 'size'), mean_return=('daily_return', 'mean'),
                     advancing=('advancing', 'sum'), declining=('declining', 'sum'), unchanged=('unchanged', 'sum')).reset_index()
    ranked = data[data.daily_return.notna()].sort_values(group + ['daily_return'] + KEYS,
                                                       ascending=[True] * len(group) + [False] + [True] * len(KEYS))
    ranked['rank'] = ranked.groupby(group).cumcount() + 1
    return aggregates, ranked[ranked['rank'] <= 10].drop(columns=['advancing', 'declining', 'unchanged'])
