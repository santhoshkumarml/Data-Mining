'''
Created on Nov 25, 2014

@author: Santhosh Kumar
'''
import SIAUtil
import dataReader
from LBP import LBP
from SIAUtil import TimeBasedGraph
from copy import deepcopy, copy
from datetime import datetime
from threading import Thread

###################################################Parallelize LBP Run Using Thread######################################################
class LBPRunnerThread(Thread):
    def __init__(self, graph, limit, name='LBPRunner'):
        super(LBPRunnerThread,self).__init__()
        self.graph = graph
        self.name = name
        self.limit = limit
        self.to_be_removed_usr_bnss_edges = set()
        
    def getFakeEdgesData(self):
        return self.to_be_removed_usr_bnss_edges
    
    def runLBP(self):
        threadedLBP = LBP(self.graph)
        threadedLBP.doBeliefPropagationIterative(self.limit)
        (fakeUsers, honestUsers, unclassifiedUsers, badProducts, goodProducts, unclassifiedProducts, fakeReviewEdges, realReviewEdges, unclassifiedReviewEdges) = \
            threadedLBP.calculateBeliefVals()
        self.to_be_removed_usr_bnss_edges = set([(threadedLBP.getEdgeDataForNodes(*edge).getUserId(),\
                                                       threadedLBP.getEdgeDataForNodes(*edge).getBusinessID())\
                             for edge in fakeReviewEdges])
        print len(self.to_be_removed_usr_bnss_edges)
        
    def run(self):
        print "Starting LBP " + self.name + " " + str(datetime.now())
        self.runLBP()
        print "Exiting " + self.name + " " + str(datetime.now())
        
###################################################INITIALIZE_PREMILINARY_STEPS##########################################################
def initialize(inputFileName):
    (parentUserIdToUserDict, parentBusinessIdToBusinessDict, parent_reviews) =\
        dataReader.parseAndCreateObjects(inputFileName)
    parent_graph = SIAUtil.createGraph(parentUserIdToUserDict,parentBusinessIdToBusinessDict,parent_reviews)

#     cross_9_months_graphs = SIAUtil.createTimeBasedGraph(parentUserIdToUserDict, parentBusinessIdToBusinessDict, parent_reviews, '9-M')
    cross_time_graphs = SIAUtil.createTimeBasedGraph(parentUserIdToUserDict,\
                                                          parentBusinessIdToBusinessDict,\
                                                           parent_reviews, '1-Y')
    beforeThreadTime = datetime.now()
    cross_time_lbp_runner_threads = []
    for time_key in cross_time_graphs.iterkeys():
        print '----------------------------------GRAPH-', time_key, '---------------------------------------------\n'
        lbp_runner = LBPRunnerThread(cross_time_graphs[time_key], 50, 'Initial LBP Runner for Time'+str(time_key))
        cross_time_lbp_runner_threads.append(lbp_runner)
        lbp_runner.start()
    for lbp_runner in cross_time_lbp_runner_threads:
        lbp_runner.join()
    afterThreadTime = datetime.now()
    print 'Time to be reduced',afterThreadTime-beforeThreadTime    
    return (cross_time_graphs, parent_graph)

###################################################################DATASTRUCTURES################################################################################
def calculateCrossTimeDs(cross_time_graphs):
    bnss_score_all_time_map = dict()
    for time_key in cross_time_graphs.iterkeys():
        bnss_score_map_for_time = {bnss.getId():bnss.getScore() for bnss in cross_time_graphs[time_key].nodes() if bnss.getNodeType()==SIAUtil.PRODUCT}
        for bnss_key in bnss_score_map_for_time.iterkeys():
            if bnss_key not in bnss_score_all_time_map:
                bnss_score_all_time_map[bnss_key] = dict()
            time_score_map = bnss_score_all_time_map[bnss_key]
            time_score_map[time_key] = bnss_score_map_for_time[bnss_key]
    return bnss_score_all_time_map

################################################ALGO FOR MERGE###############################################################
def calculateMergeAbleAndNotMergeableBusinessesAcrossTime(cross_time_graphs, parent_graph):
    bnss_score_all_time_map = calculateCrossTimeDs(cross_time_graphs)
    # calculate interesting businesses across time
    mergeable_businessids = dict()
    not_mergeable_businessids = dict()
    for bnss_key in bnss_score_all_time_map.iterkeys():
        time_score_map = bnss_score_all_time_map[bnss_key]
        scores = [time_score_map[time_key][1] for time_key in time_score_map.iterkeys()]
        good_scores = SIAUtil.rm_outlier(scores)
#         print 'IN: ', scores #  REMOVE
#         print 'OP: ', good_scores
#         print '*'*10
        for time_key in time_score_map.iterkeys():
            score = time_score_map[time_key][1]
            if(score in good_scores):
                if time_key not in mergeable_businessids:
                    mergeable_businessids[time_key] = set()
                mergeable_businessids[time_key].add(bnss_key)
            else:
                if time_key not in not_mergeable_businessids:
                    not_mergeable_businessids[time_key] = set()
                not_mergeable_businessids[time_key].add(bnss_key)
                
    for time_key in not_mergeable_businessids.iterkeys():
        print 'Interesting businesses in  time:', time_key,len(not_mergeable_businessids[time_key])
    for time_key in mergeable_businessids.iterkeys():
        print 'Not Interesting businesses in time:', time_key,len(mergeable_businessids[time_key])
    return (mergeable_businessids,not_mergeable_businessids)

def mergeTimeBasedGraphsWithMergeableIds(mergeable_businessids, cross_time_graphs):
    alltimeD_access_merge_graph = TimeBasedGraph()
    all_time_userIdToUserDict = dict()
    all_time_bnssIdToBnssDict = dict()
    for time_key in cross_time_graphs.iterkeys():
        for siaObject in cross_time_graphs[time_key].nodes():
            if siaObject.getId() in all_time_userIdToUserDict or siaObject.getId() in all_time_bnssIdToBnssDict:
                continue
            newSiaObject = copy(siaObject)
            newSiaObject.reset()
            if(newSiaObject.getNodeType() == SIAUtil.USER):
                all_time_userIdToUserDict[newSiaObject.getId()] = newSiaObject
            else:
                all_time_bnssIdToBnssDict[newSiaObject.getId()] = newSiaObject
            alltimeD_access_merge_graph.add_node(newSiaObject)
    
    alltimeD_access_merge_graph.initialize(all_time_userIdToUserDict, all_time_bnssIdToBnssDict)
    # create a new super graph with all nodes    
    # whatever businesses did not drastically change, get all the edges
    # of the business and add them to new super graph    
    for time_key in mergeable_businessids:
            graph = cross_time_graphs[time_key]
            for bnssid in mergeable_businessids[time_key]:
                bnss = graph.getBusiness(bnssid)
                usrs = graph.neighbors(bnss)
                for usr in usrs:
                    review = deepcopy(graph.get_edge_data(usr,bnss)[SIAUtil.REVIEW_EDGE_DICT_CONST])
                    alltimeD_access_merge_graph.add_edge(alltimeD_access_merge_graph.getBusiness(bnss.getId()),\
                                                         alltimeD_access_merge_graph.getUser(usr.getId()),\
                                                          {SIAUtil.REVIEW_EDGE_DICT_CONST:review})
                    graph.remove_edge(usr,bnss)

    print len(alltimeD_access_merge_graph.nodes()),len(alltimeD_access_merge_graph.edges())
    
    return alltimeD_access_merge_graph

def mergeTimeBasedGraphsWithNotMergeableIds(alltimeD_access_merge_graph,not_mergeable_businessids, cross_time_graphs):
    # whatever businesses did drastically change,
    # we will copy the super graph and try adding these edges to the copied
    # graph and run LBP
    to_be_removed_edge_between_user_bnss = set()
    
    copy_merge_lbp_runner_threads = []
    beforeThreadTime = datetime.now()
    for time_key in not_mergeable_businessids:
        copied_all_timeD_access_merge_graph =  deepcopy(alltimeD_access_merge_graph)
        graph = cross_time_graphs[time_key]
        for bnssid in not_mergeable_businessids[time_key]:
            bnss = graph.getBusiness(bnssid)
            usrs = graph.neighbors(bnss)
            for usr in usrs:
                review = deepcopy(graph.get_edge_data(usr,bnss)[SIAUtil.REVIEW_EDGE_DICT_CONST])
                copied_all_timeD_access_merge_graph.add_edge(copied_all_timeD_access_merge_graph.getBusiness(bnss.getId()),\
                                                             copied_all_timeD_access_merge_graph.getUser(usr.getId()),
                                                             {SIAUtil.REVIEW_EDGE_DICT_CONST:review})    
        copy_merge_lbp_runner = LBPRunnerThread(copied_all_timeD_access_merge_graph, 10, 'LBP Runner For Not mergeableIds'+str(time_key))
        copy_merge_lbp_runner_threads.append(copy_merge_lbp_runner)
        copy_merge_lbp_runner.start()
        
    for copy_merge_lbp_runner in copy_merge_lbp_runner_threads:
        copy_merge_lbp_runner.join()
    
    afterThreadTime = datetime.now()
    print 'Time to be reduced', afterThreadTime-beforeThreadTime
        
    for copy_merge_lbp_runner in copy_merge_lbp_runner_threads:
        print 'Copy merge runner', len(copy_merge_lbp_runner.getFakeEdgesData())
        to_be_removed_edge_between_user_bnss = to_be_removed_edge_between_user_bnss.union(copy_merge_lbp_runner.getFakeEdgesData())
    
    #from the drastically change businesses we have find out all fake edges in the above step
    # without them add rest of the edges to the super graph and run LBP on it
    for time_key in not_mergeable_businessids:
        graph = cross_time_graphs[time_key]
        for bnssid in not_mergeable_businessids[time_key]:
            bnss = graph.getBusiness(bnssid)
            usrs = graph.neighbors(bnss)
            for usr in usrs:
                if (usr.getId(),bnss.getId()) not in to_be_removed_edge_between_user_bnss:
                    review = deepcopy(graph.get_edge_data(usr,bnss)[SIAUtil.REVIEW_EDGE_DICT_CONST])
                    alltimeD_access_merge_graph.add_edge(alltimeD_access_merge_graph.getBusiness(bnss.getId()),\
                                                         alltimeD_access_merge_graph.getUser(usr.getId()),\
                                                          {SIAUtil.REVIEW_EDGE_DICT_CONST:review})               
    
    print "------------------------------------Running Final Merge LBP--------------------------------------"
    merge_lbp = LBP(alltimeD_access_merge_graph)
    merge_lbp.doBeliefPropagationIterative(10)
    (fakeUsers, honestUsers,unclassifiedUsers,\
     badProducts,goodProducts, unclassifiedProducts,\
     fakeReviewEdges, realReviewEdges,unclassifiedReviewEdges) = merge_lbp.calculateBeliefVals()
    for edge in fakeReviewEdges:
        to_be_removed_edge_between_user_bnss.add((merge_lbp.getEdgeDataForNodes(*edge).getUserId(),\
                                                    merge_lbp.getEdgeDataForNodes(*edge).getBusinessID())) 
    return to_be_removed_edge_between_user_bnss
#############################################################################################################################
def runParentLBPAndCompareStatistics(certifiedFakesFromTemporalAlgo, parent_graph):
    print "------------------------------------Running Parent LBP along with all Time Edges--------------------------------------"
    # run LBP on a non temporal full graph for comparison  
    parent_lbp = LBP(parent_graph)
    parent_lbp.doBeliefPropagationIterative(10)
    (parent_lbp_fakeUsers, parent_lbp_honestUsers,parent_lbp_unclassifiedUsers,\
          parent_lbp_badProducts, parent_lbp_goodProducts, parent_lbp_unclassifiedProducts,\
          parent_lbp_fakeReviewEdges, parent_lbp_realReviewEdges, parent_lbp_unclassifiedReviewEdges) = parent_lbp.calculateBeliefVals()

    print "-----------------------------------------------Statistics------------------------------------------------------------------"
    fakeReviewInParentLBP = set([parent_lbp.getEdgeDataForNodes(*edge).getId() for edge in parent_lbp_fakeReviewEdges]) 
    fakeReviewsFromYelp   = set([parent_lbp.getEdgeDataForNodes(*edge).getId() for edge in parent_graph.edges()\
                                  if not parent_lbp.getEdgeDataForNodes(*edge).isRecommended()] )
    fakeReviewsFromTemporalAlgo = set([parent_lbp.getReviewIdsForUsrBnssId(usrId, bnssId) for (usrId,bnssId) in certifiedFakesFromTemporalAlgo])
    
    #Accuracy
    print 'Temporal Algo',len(fakeReviewsFromTemporalAlgo)
    print 'LBP',len(fakeReviewInParentLBP)
    print 'Yelp', len(fakeReviewsFromYelp)
    print 'Intersection of Yelp with TemporalLBP:', len(fakeReviewsFromYelp&fakeReviewsFromTemporalAlgo)
    print 'Intersection of Yelp with LBP:', len(fakeReviewsFromYelp&fakeReviewInParentLBP)
    print 'Intersection of Temporal LBP with LBP:', len(fakeReviewsFromTemporalAlgo&fakeReviewInParentLBP)
    print 'Intersection Across Yelp,Temporal and LBP',len(fakeReviewsFromTemporalAlgo&fakeReviewInParentLBP&fakeReviewsFromYelp)
    
    print 'Yelp-TemporalLBP:',len(fakeReviewsFromYelp-fakeReviewsFromTemporalAlgo)
    print 'TemporalLBP-Yelp:',len(fakeReviewsFromTemporalAlgo-fakeReviewsFromYelp)
    
    print 'Yelp-LBP:', len(fakeReviewsFromYelp-fakeReviewInParentLBP)
    print 'LBP-Yelp:', len(fakeReviewInParentLBP-fakeReviewsFromYelp)
    
    print 'Temporal LBP-LBP:', len(fakeReviewsFromTemporalAlgo-fakeReviewInParentLBP)
    print 'LBP-TemporalLBP:', len(fakeReviewInParentLBP-fakeReviewsFromTemporalAlgo)


if __name__ == '__main__':
    inputFileName = 'E:\\workspace\\\dm\\data\\crawl_new\\sample_master.txt'
    #inputFileName = 'E:\\workspace\\\dm\\data\\crawl_old\\o_new_2.txt'
    beforeRunTime = datetime.now()
    #inputFileName = '/home/rami/Downloads/sample_master.txt'
    
    beforeTemporalTime = datetime.now()
    (cross_graphs, pg) = initialize(inputFileName)
    (mIds,nonMids) = calculateMergeAbleAndNotMergeableBusinessesAcrossTime(cross_graphs, pg)
    time_merge_graph = mergeTimeBasedGraphsWithMergeableIds(mIds, cross_graphs)
    fakesFromTemporalAlgo = mergeTimeBasedGraphsWithNotMergeableIds(time_merge_graph, nonMids, cross_graphs)
    afterTemporalTime = datetime.now()
    
    beforeParentLBP = datetime.now()
    runParentLBPAndCompareStatistics(fakesFromTemporalAlgo, pg)
    afterParentLBP = datetime.now()
    
    afterRunTime = datetime.now()
    
    print 'Total Run Time', afterRunTime-beforeRunTime,\
            'Run Time of Temporal LBP Algo',afterTemporalTime-beforeTemporalTime,\
            'Run Time of LBP Algo',afterParentLBP-beforeParentLBP