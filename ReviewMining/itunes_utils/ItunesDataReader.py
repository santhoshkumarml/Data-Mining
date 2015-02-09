'''
Created on Feb 6, 2015

@author: santhosh
'''
import pandas as pd
import sys
from os.path import join
from util.SIAUtil import user, business, review
from datetime import datetime

#appid,review id,userid,username,stars,version,date,number of helpful votes,total votes,unix timestamp
META_BNSS_ID = 'bnss_id'
META_REVIEW_ID = 'review_id'
META_USER_ID = 'user_id'
META_USER_NAME = 'username'
META_STARS = 'stars'
META_BNSS_VERSION = 'version'
META_DATE  = 'date'
META_HELPFUL_VOTES ='Helpful Votes' 
META_TOTAL_VOTES = 'Total Votes'
META_TIMESTAMP = 'Timestamp'
META_COLS = [META_BNSS_ID,  META_REVIEW_ID, META_USER_ID, META_USER_NAME, \
             META_STARS, META_BNSS_VERSION, META_DATE, META_HELPFUL_VOTES, \
             META_TOTAL_VOTES, META_TIMESTAMP]

META_IDX_DICT = {META_COLS[i]:i for i in range(len(META_COLS))}

#appid,review id,title,content
BNSS_ID = 'bnss_id'
REVIEW_ID = 'review_id'
TITLE = 'title'
CONTENT = 'content' 
COLS = [BNSS_ID, REVIEW_ID, TITLE, CONTENT]

REVW_IDX_DICT = {COLS[i]:i for i in range(len(COLS))}

META_FILE = 'itunes3_reviews_meta.csv'
REVIEW_FILE = 'itunes3_reviews_text.csv'

class ItunesDataReader:
    def __init__(self):
        self.usrIdToUsrDict = {}
        self.bnssIdToBnssDict = {}
        self.reviewIdToReviewDict = {}
        
    def readData(self, reviewFolder):
        reviewMetaFile = join(reviewFolder, META_FILE)
        
        df1 = pd.read_csv(reviewMetaFile,escapechar='\\',header=None,\
                              dtype=object, names = META_COLS)
        
        #df1 =  df1.dropna(axis=0, how='all')
        reviewFile = join(reviewFolder, REVIEW_FILE)
        
        df2 = pd.read_csv(reviewFile,escapechar='\\',header=None,\
                              dtype=object, names = COLS)
        
        df2 = df2.dropna(axis=0, how='all')
        
        for row in df1.itertuples():
            row = row[0]
            bnss_id = row[META_IDX_DICT[META_BNSS_ID]]
            user_id = row[META_IDX_DICT[META_USER_ID]]
            user_name = row[META_IDX_DICT[META_USER_NAME]]
            review_id = row[META_IDX_DICT[META_REVIEW_ID]]
            stars = row[META_IDX_DICT[META_STARS]]
            review_date = row[META_IDX_DICT[META_DATE]]
            
            print bnss_id, user_id, user_name, review_id, stars, review_date
            
            if bnss_id not in self.bnssIdToBnssDict:
                self.bnssIdToBnssDict[bnss_id] = business(bnss_id, bnss_id)
            bnss = self.bnssIdToBnssDict[bnss_id]
            
            if user_id not in self.usrIdToUsrDict:
                self.usrIdToUsrDict[user_id] = user(user_id, user_name)    
            usr = self.usrIdToUsrDict[user_id]
            
            date_object = datetime.strptime(review_date, '%b %d,%Y')
            
            revw = review(review_id, usr.getId(), bnss.getId(), stars, date_object)
            
            self.reviewIdToReviewDict[review_id] = revw
    
            
        for row in df2.iterrows():
            print row
            review_id = row[REVW_IDX_DICT[REVIEW_ID]]
            review_text = row[REVW_IDX_DICT[CONTENT]]
            self.reviewIdToReviewDict[review_id].setReviewText(review_text)
        
        print len(self.reviewIdToReviewDict.keys())