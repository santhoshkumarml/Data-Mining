'''
Created on Jan 4, 2015

@author: Santhosh
'''
from util.SIAUtil import business, user, review
from os import listdir
from os.path import isfile, join
import re
import sys

NOT_RECOMMENDED = 'nonReccomended'
RECOMMENDED = 'Reccomended'
ADDRESS = 'Address'
RATING = 'Rating'
REVIEW_COUNT = 'reviewCount'
FRIEND_COUNT = 'friendCount'
NAME = 'Name'
FRIEND_COUNT = 'friendCount'
USR_LOCATION = 'Place'
REVIEW_TEXT = 'ReviewComment'
REVIEW_DATE = 'Date'
IMG_SRC = 'imgSrc'
URL = 'URL'

class ScrappedDataReader:
    def __init__(self):
        self.usrIdToUsrDict = {}
        self.bnssIdToBnssDict = {}
        self.reviewIdToReviewDict = {}
        
    def getUsrIdToUsrDict(self):
        return self.usrIdToUsrDict
    
    def getBnssIdToBnssDict(self):
        return self.bnssIdToBnssDict
    
    def getReviewIdToReviewDict(self):
        return self.reviewIdToReviewDict
        
    def readDataForBnss(self, inputDirName, fileName, reviewIDIncrementer):
        content = 'data='
        with open(join(inputDirName, fileName), mode='r') as f:
            data = dict()
            content = content+f.readline()
            exec(content)
            bnssName = fileName.strip('.txt')
            bnssAddress = data[ADDRESS]
            bnssUrl = data[URL]
            bnssId = (bnssUrl, bnssAddress)
            
            if bnssId in self.bnssIdToBnssDict:
                bnss = self.bnssIdToBnssDict[bnssId]
            else:
                bnss = business(bnssId, bnssName, url=bnssUrl)     
                self.bnssIdToBnssDict[bnss.getId()] = bnss
            
            nrReviews = data[NOT_RECOMMENDED]
            rReviews = data[RECOMMENDED]
            #print bnssName, len(rReviews), len(nrReviews)
                
            for r in rReviews:
                reviewIDIncrementer += 1
                review_rating = r[RATING]
                review_id = reviewIDIncrementer
                review_text = r[REVIEW_TEXT]
                review_date = r[REVIEW_DATE].split('Updated review')[0]
                    
                usr_location = r[USR_LOCATION]
                usr_name = r[NAME]
                usr_review_count = r[REVIEW_COUNT]
                usr_friend_count = r[FRIEND_COUNT]
                if not usr_name or usr_name=='':
                    print "Continue"
                    continue
                usrId = r['usrId']
                usrExtra = (usr_location, usr_review_count, usr_friend_count)
                
                if usrId in self.usrIdToUsrDict:
                    usr = self.usrIdToUsrDict[usrId]
                else:
                    usr = user(usrId, usr_name, usrExtra)
                    self.usrIdToUsrDict[usr.getId()] = usr
                    
                revw = review(review_id, usr.getId(), bnss.getId(), review_rating, review_date, review_text, True)
                self.usrIdToUsrDict[usr.getId()] = usr
                self.reviewIdToReviewDict[revw.getId()] = revw

                    
            for nr in nrReviews:
                reviewIDIncrementer += 1
                review_rating = nr[RATING]
                review_id = reviewIDIncrementer
                review_text = nr[REVIEW_TEXT]
                review_date = nr[REVIEW_DATE].split('Updated review')[0]
                    
                usr_location = nr[USR_LOCATION]
                usr_name = nr[NAME]
                usr_review_count = nr[REVIEW_COUNT]
                usr_friend_count = nr[FRIEND_COUNT]
                if not usr_name or usr_name=='':
                    print "Continue"
                    continue
                usrId = nr['usrId']
                if usrId in self.usrIdToUsrDict:
                    usr = self.usrIdToUsrDict[usrId]
                else:
                    usrExtra = (usr_location, usr_review_count, usr_friend_count)
                    usr = user(usrId, usr_name, usrExtra)
                    self.usrIdToUsrDict[usr.getId()] = usr
                    
                revw = review(review_id, usr.getId(), bnss.getId(), review_rating, review_date, review_text, False)
            
                self.reviewIdToReviewDict[revw.getId()] = revw
            
            
            return reviewIDIncrementer
        
    def readData(self, inputDirName):
        zipDirectories = [join(inputDirName,f) for f in listdir(inputDirName) if not isfile(join(inputDirName,f)) ]
        onlyfiles = [(zipDir,f) for zipDir in zipDirectories for f in listdir(zipDir) if isfile(join(zipDir,f))]
        reviewIDIncrementer = 0
        for dirName,fileName in onlyfiles:
            reviewIDIncrementer = self.readDataForBnss(dirName, fileName, reviewIDIncrementer)
        return (self.usrIdToUsrDict, self.bnssIdToBnssDict, self.reviewIdToReviewDict)