'''
Created on Feb 19, 2015

@author: santhosh
'''

from datetime import datetime
from util import StatConstants
import anomaly_detection
import changefinder
import cusum
import numpy

def detect_outliers_using_cusum(x, threshold=1):
    x = numpy.atleast_1d(x).astype('float64')
    gp, gn = numpy.zeros(x.size), numpy.zeros(x.size)
    ta, tai, tapi, tani = numpy.array([[], [], [], []], dtype=int)
    tap, tan = 0, 0
    # Find changes (online form)
    i = 1
    while i < x.size:
        idx = 0 if not ta.size else ta[-1]
        prev_idx = 0 if ta.size <=1 else ta[-2]
        # s = x[i] - x[i-1]
        # s = -1
        if prev_idx != idx:
            sd = numpy.std(x[prev_idx:idx])
            s = (threshold/sd)*(x[i] - numpy.mean(x[idx:i]) - (threshold/2))
        else:
            s = x[i] - numpy.mean(x[idx:i])
        #print i, idx, x[i], numpy.mean(x[idx:i]),x[i] - numpy.mean(x[idx:i]), gp[i-1]+s, gn[i-1]-s

        gp[i] = gp[i-1] + s  # cumulative sum for + change
        gn[i] = gn[i-1] - s  # cumulative sum for - change
        if gp[i] < 0:
            gp[i], tap = 0, i
        if gn[i] < 0:
            gn[i], tan = 0, i
        if gp[i] > threshold or gn[i] > threshold:
            ta = numpy.append(ta, i)
            if gp[i] > threshold:
                tai = numpy.append(tai, tap)
                tapi = numpy.append(tapi,i)
            else:
                tai = numpy.append(tai, tan)
                tani = numpy.append(tani,i)
            gp[i], gn[i] = 0, 0
            # gp[i], gn[i] = threshold, threshold      # reset alarm
    return ta, tai, tapi, tani




def twitterAnomalyDetection(dates, values):
    import rpy2.robjects as robjects
    from rpy2.robjects.packages import importr
    importr("AnomalyDetection")
    anomaly_detection = robjects.r['AnomalyDetectionTs']

    # robjects.r('''
    #     rdateFn <- function(d , m, y) {
    #         dat <- paste(paste(toString(d),toString(m),sep="/"),toString(y), sep="/")
    #         return(dat)
    #     }
    #     ''')
    # rdateFn = robjects.globalenv['rdateFn']

    dates = []
    dates = [datetime.combine(dates[i], datetime.min.time()) for i in range(len(dates))]
    date_value_dict = {'a':robjects.POSIXct(dates), 'b':robjects.IntVector(values)}
    dataf = robjects.DataFrame(date_value_dict)
    res = anomaly_detection(dataf, plot= True)
    anoms_data_f = res[res.names.index('anoms')]
    anoms_dates = set()
    for d in anoms_data_f.rx2(1):
        anoms_dates.add(datetime.fromtimestamp(d).date())
    idxs = []
    dates = [dates[i].date() for i in range(len(dates))]
    for i in range(len(dates)):
        if dates[i] in anoms_dates:
            idxs.append(i)
    values = numpy.atleast_1d(values).astype('int64')
    return idxs

# r - Coefficient of forgetting type AR model. 0 <r <1
# order - Degree of forgetting type AR model
# smooth - section length of time to be moving average smoothing the calculated outliers score

def detectChPtsAndOutliers(statistics_for_bnss):
    chPtsOutliers = dict()
    beforeDetection = datetime.now()
    firstKey = statistics_for_bnss[StatConstants.FIRST_TIME_KEY]
    chPtsOutliers= dict()
    for measure_key in StatConstants.MEASURES:
        if measure_key in statistics_for_bnss:
            data = statistics_for_bnss[measure_key][firstKey:]
            algo, params = StatConstants.MEASURES_CHANGE_FINDERS[measure_key]
            if algo == StatConstants.AR_UNIFYING:
                r,order,smooth = params
                cf = changefinder.ChangeFinder(r,order,smooth)
                change_scores = []
                for i in range(len(data)):
                    score = cf.update(data[i])
                    change_scores.append(score)
                    chPtsOutliers[measure_key] = change_scores
            elif algo == StatConstants.CUSUM:
                chPtsOutliers[measure_key] = cusum.detect_cusum(data, threshold=params, show=False)
            elif algo == StatConstants.TWITTER_SEASONAL_ANOM_DETECTION:
                chPtsOutliers[measure_key] = twitterAnomalyDetection(data,data)
    
    afterDetection = datetime.now()
    print 'Time Taken For Anamoly Detection for Bnss Key',statistics_for_bnss[StatConstants.BNSS_ID],\
        ':', afterDetection-beforeDetection
    return chPtsOutliers