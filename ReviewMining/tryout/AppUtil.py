import math
import os
import pickle
from datetime import datetime

import numpy

from anomaly_detection import AnomalyDetector
from itunes_utils.ItunesDataReader import ItunesDataReader
from statistics import business_statistics_generator
from util import GraphUtil, SIAUtil, StatConstants, PlotUtil

SCORES_LOG_FILE = 'scores_with_outliers.log'
BNSS_STATS_FOLDER = 'bnss_stats'
USR_REVIEW_CNT_FILE = 'usr_review_cnt.txt'
BNSS_REVIEW_CNT_FILE = 'bnss_review_cnt.txt'


#1/(1+ (k**2)) = percent
#k = math.sqrt( (1-percent)/ percent)
#k = math.sqrt(19) for 5% (i.e. 0.05)

def determinKForPercent(percent):
    return math.sqrt((1-percent)/percent)

def getThreshold(data, percent):
    m = numpy.mean(data)
    std = numpy.std(data)
    return (m + (determinKForPercent(percent)*std))

def readData(csvFolder,readReviewsText=False):
    rdr = ItunesDataReader()
    (usrIdToUserDict, bnssIdToBusinessDict, reviewIdToReviewsDict) = rdr.readData(csvFolder, readReviewsText)
    return bnssIdToBusinessDict, reviewIdToReviewsDict, usrIdToUserDict

def serializeBnssStats(bnss_key, plotDir, statistics_for_bnss):
    bnss_file_name = os.path.join(plotDir, bnss_key)
    print 'Serializing to file', bnss_file_name
    if not os.path.exists(bnss_file_name):
        with open(bnss_file_name, 'w') as f:
            pickle.dump(statistics_for_bnss, f)


def deserializeBnssStats(bnss_key, statsDir):
    return pickle.load(open(os.path.join(statsDir, bnss_key)))


def readAndGenerateStatistics(csvFolder, plotDir, timeLength = '1-W'):
    # Read data
    bnssIdToBusinessDict, reviewIdToReviewsDict, usrIdToUserDict = readData(csvFolder)
    # Construct Graphs
    superGraph, cross_time_graphs = GraphUtil.createGraphs(usrIdToUserDict, \
                                                           bnssIdToBusinessDict, \
                                                           reviewIdToReviewsDict, timeLength)
    if not os.path.exists(plotDir):
        os.makedirs(plotDir)
    bnssKeys = [bnss_key for bnss_key, bnss_type in superGraph.nodes() \
                if bnss_type == SIAUtil.PRODUCT]
    bnssKeys = sorted(bnssKeys, reverse=True, key=lambda x: len(superGraph.neighbors((x, SIAUtil.PRODUCT))))
    # bnssKeys = ['363590051']
    # bnssKeys = bnssKeys[:2]
    measuresToBeExtracted = [measure for measure in StatConstants.MEASURES \
                             if measure != StatConstants.MAX_TEXT_SIMILARITY and measure != StatConstants.TF_IDF]
    lead_signals = [measure for measure in measuresToBeExtracted if measure in StatConstants.MEASURE_LEAD_SIGNALS]
    measuresToBeExtracted = [measure for measure in set(lead_signals).union(set(measuresToBeExtracted))]
    return bnssKeys, cross_time_graphs, measuresToBeExtracted, superGraph


def doSerializeAllBnss(csvFolder, plotDir, timeLength = '1-W'):
    bnssKeys, cross_time_graphs, measuresToBeExtracted, superGraph = readAndGenerateStatistics(csvFolder, plotDir)
    for bnssKey in bnssKeys:
        statistics_for_bnss = business_statistics_generator.extractBnssStatistics(
            superGraph, \
            cross_time_graphs, \
            plotDir, bnssKey, \
            timeLength, \
            measuresToBeExtracted, logStats=False)
        serializeBnssStats(bnssKey, plotDir, statistics_for_bnss)


def intersection_between_users(usr_ids_for_bnss_in_time_window, bnssKey, superGraph):
    usrs_for_this_bnss = set([usrId for usrId, usr_type in superGraph.neighbors((bnssKey, SIAUtil.PRODUCT))])
    ins = usr_ids_for_bnss_in_time_window.intersection(usrs_for_this_bnss)
    if len(ins) > 10:
        print bnssKey, ins
    return len(ins)


def findUsersInThisTimeWindow(bnssKey, time_window, csvFolder, plotDir, timeLength = '1-W'):
     # Read data
    bnssIdToBusinessDict, reviewIdToReviewsDict, usrIdToUserDict = readData(csvFolder, readReviewsText=False)

    # Construct Graphs
    superGraph, cross_time_graphs = GraphUtil.createGraphs(usrIdToUserDict,
                                                           bnssIdToBusinessDict,
                                                           reviewIdToReviewsDict, timeLength)
    del superGraph

    usr_to_reviews_dict = readReviewsForBnssOrUser(plotDir, node_type=SIAUtil.USER)

    usr_ids_for_bnss_in_time_window = []

    lb, ub = time_window
    time_window = [idx for idx in range(lb, ub+1)]
    for time_key in time_window:
         time_g = cross_time_graphs[time_key]
         if (bnssKey, SIAUtil.PRODUCT) not in time_g:
             continue
         usr_ids_for_bnss_in_time_window = usr_ids_for_bnss_in_time_window + \
                                           [usrId for (usrId, usr_type) in time_g.neighbors((bnssKey, SIAUtil.PRODUCT))]
    # usr_ids_for_bnss_in_time_window = set(usr_ids_for_bnss_in_time_window)

    usr_ids_for_bnss_in_time_window = sorted([(usr, usr_to_reviews_dict[usr])
                                              for usr in usr_ids_for_bnss_in_time_window], key=lambda x: x[1])
    for usr in usr_ids_for_bnss_in_time_window:
        print usr


    # bnssKeys = set([bnssId for usrId in usr_ids_for_bnss_in_time_window for bnssId, bnssType in superGraph.neighbors((usrId, SIAUtil.USER))])
    # bnssKeys = [(bnssId, intersection_between_users(usr_ids_for_bnss_in_time_window, bnssId, superGraph)) for bnssId in bnssKeys]
    # bnssKeys = sorted(bnssKeys, reverse=True, key=lambda x: x[1])
    # print bnssKeys


def logAllUsrStats(csvFolder, plotDir, timeLength = '1-W'):
    # Read data
    bnssIdToBusinessDict, reviewIdToReviewsDict, usrIdToUserDict = readData(csvFolder)
    # Construct Graphs
    superGraph, cross_time_graphs = GraphUtil.createGraphs(usrIdToUserDict, \
                                                           bnssIdToBusinessDict, \
                                                           reviewIdToReviewsDict, timeLength)
    if not os.path.exists(plotDir):
        os.makedirs(plotDir)
    usrKeys = [usr_key for usr_key, usr_type in superGraph.nodes() \
                if usr_type == SIAUtil.USER]
    for usr_key in usrKeys:
        usrStatFilePath = os.path.join(plotDir, usr_key+'.stats')
        with open(usrStatFilePath, 'w') as usrStatFile:
            usrStatFile.write('--------------------------------------------------------------------------------------------------------------------\n')
            usrStatFile.write('Statistics for User:'+usr_key+'\n')
            neighboring_bnss_nodes = superGraph.neighbors((usr_key, SIAUtil.USER))
            reviews_for_usr = [superGraph.getReview(usr_key, bnssId) for (bnssId, bnss_type) in neighboring_bnss_nodes]
            usrStatFile.write('Reviews for this usr:')
            usrStatFile.write('Number of reviews:'+str(len(neighboring_bnss_nodes)))
            usrStatFile.write('\n')
            reviews_sorted = sorted(reviews_for_usr, key=lambda key: SIAUtil.getDateForReview(key))
            for review in reviews_sorted:
                usrStatFile.write(review.toString())
                usrStatFile.write('\n')


def readReviewsForBnssOrUser(plotDir, node_type = SIAUtil.PRODUCT):
    file_name = BNSS_REVIEW_CNT_FILE
    node_type_to_reviews_dict = dict()
    prefix = 'node_type_to_reviews_dict'
    if node_type == SIAUtil.USER:
        file_name = USR_REVIEW_CNT_FILE
    with open(os.path.join(plotDir, file_name)) as f:
        string = prefix + '=' + f.read()
        exec(string)
    return node_type_to_reviews_dict

def logReviewsForUsrBnss(csvFolder, plotDir, timeLength='1-W'):
    # Read data
    bnssIdToBusinessDict, reviewIdToReviewsDict, usrIdToUserDict = readData(csvFolder)
    # Construct Graphs
    superGraph, cross_time_graphs = GraphUtil.createGraphs(usrIdToUserDict, \
                                                           bnssIdToBusinessDict, \
                                                           reviewIdToReviewsDict, timeLength)
    if not os.path.exists(plotDir):
        os.makedirs(plotDir)
    for key in cross_time_graphs.keys():
        del cross_time_graphs[key]

    usr_to_no_of_reviews_dict = dict()
    bnss_to_no_of_reviews_dict = dict()

    usrKeys = [usr_key for usr_key, usr_type in superGraph.nodes() \
               if usr_type == SIAUtil.USER]

    for usrKey in usrKeys:
        no_of_reviews_for_usr = len(superGraph.neighbors((usrKey, SIAUtil.USER)))
        usr_to_no_of_reviews_dict[usrKey] = no_of_reviews_for_usr

    with open(os.path.join(plotDir, USR_REVIEW_CNT_FILE), 'w') as f:
        f.write(str(usr_to_no_of_reviews_dict))

    bnssKeys = [bnss_key for bnss_key, bnss_type in superGraph.nodes() \
               if bnss_type == SIAUtil.PRODUCT]


    for bnssKey in bnssKeys:
        no_of_reviews_for_bnss = len(superGraph.neighbors((bnssKey, SIAUtil.PRODUCT)))
        bnss_to_no_of_reviews_dict[bnssKey] = no_of_reviews_for_bnss

    with open(os.path.join(plotDir, BNSS_REVIEW_CNT_FILE), 'w') as f:
        f.write(str(bnss_to_no_of_reviews_dict))


def logStats(bnssKey, plotDir, chPtsOutliers, firstTimeKey):
    measure_log_file = open(os.path.join(plotDir, SCORES_LOG_FILE), 'a')
    chPtsOutliers[StatConstants.BNSS_ID] = bnssKey
    chPtsOutliers[StatConstants.FIRST_TIME_KEY] = firstTimeKey
    measure_log_file.write(str(chPtsOutliers)+"\n")
    measure_log_file.close()
    del chPtsOutliers[StatConstants.BNSS_ID]
    del chPtsOutliers[StatConstants.FIRST_TIME_KEY]


def detectAnomaliesForBnss(bnssKey, statistics_for_current_bnss, timeLength, find_outlier_idxs=True):
    beforeAnomalyDetection = datetime.now()

    chPtsOutliers = AnomalyDetector.detectChPtsAndOutliers(statistics_for_current_bnss, timeLength,
                                                           find_outlier_idxs)
    afterAnomalyDetection = datetime.now()

    print 'Anomaly Detection Time for bnss:', bnssKey, 'in', afterAnomalyDetection-beforeAnomalyDetection

    return chPtsOutliers


def plotBnssStats(bnss_key, statistics_for_bnss, chPtsOutliers, plotDir, measuresToBeExtracted, timeLength):
    beforePlotTime = datetime.now()
    lead_idxs = set()
    for measure_key in StatConstants.MEASURE_LEAD_SIGNALS:
        algo = chPtsOutliers[measure_key].keys()[0]
        avg_idxs, chOutlierScores = chPtsOutliers[measure_key][algo]
        lead_idxs |= set(avg_idxs)
    lead_idxs = sorted(lead_idxs)
    PlotUtil.plotMeasuresForBnss(statistics_for_bnss, chPtsOutliers, plotDir, \
                                 measuresToBeExtracted, lead_idxs, timeLength)
    afterPlotTime = datetime.now()
    print 'Plot Generation Time for bnss:', bnss_key, 'in', afterPlotTime-beforePlotTime


def detectOutliersUsingAlreadyGeneratedScores(all_scores, statistics_for_bnss, chPtsOutliers, bnssKey):
    avg_idxs, avg_scores = chPtsOutliers[StatConstants.AVERAGE_RATING][StatConstants.CUSUM]
    for measure_key in chPtsOutliers.keys():
        all_algo_scores = chPtsOutliers[measure_key]
        if measure_key in StatConstants.MEASURE_LEAD_SIGNALS or measure_key == StatConstants.BNSS_ID \
                or measure_key == StatConstants.FIRST_TIME_KEY:
            continue
        for algo in all_algo_scores.keys():
            chPtsOutlierIdxs, chPtsOutlierScores = all_algo_scores[algo]
            permitted_idxs = set()
            chPtsOutlierIdxs = []
            if algo == StatConstants.LOCAL_AR:
                windows = AnomalyDetector.getRangeIdxs(avg_idxs)
                permitted_idxs = set([idx for idx in range(idx1, idx2+1) for idx1, idx2 in windows])
            else:
                permitted_idxs = set([idx for idx in range(0, len(chPtsOutlierScores))])
            for idx in range(0, len(chPtsOutlierScores)):
                if idx in permitted_idxs:
                    if chPtsOutlierScores[idx] > StatConstants.MEASURE_CHANGE_LOCAL_AR_THRES[measure_key]:
                        chPtsOutlierIdxs.append(idx)
            all_algo_scores[algo] = (chPtsOutlierIdxs, chPtsOutlierScores)
        chPtsOutliers[measure_key] = all_algo_scores
    return chPtsOutliers


def readScoreFromScoreLogForBnss(string):
    chPtsOutliers = dict()
    string.strip('\r')
    string.strip('\n')
    string = "chPtsOutliers=" + string
    try:
        exec (string)
    except:
        pass
    return chPtsOutliers