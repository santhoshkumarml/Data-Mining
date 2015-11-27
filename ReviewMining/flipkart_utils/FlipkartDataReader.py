__author__ = 'santhosh'
import datetime
import os
import sys
from util import SIAUtil

import pandas

REVIEW_ID = 'Id'
BNSS_ID = 'property_id'
USER_ID = 'user_id'
RATING = 'rating'
LAST_MODIFIED_TIMESTAMP = 'last modified'
CREATE_TIMESTAMP = 'create stamp'
REVIEW_TEXT = 'text'

RATING_CSV = 'ProductRatings_processed.csv'
REVIEW_CSV = 'ProductReviews_processed.csv'
RATING_CSV_COLS = [REVIEW_ID, BNSS_ID, USER_ID, RATING, CREATE_TIMESTAMP]
REVIEW_CSV_COLS = [REVIEW_ID, BNSS_ID, USER_ID, REVIEW_TEXT]

class FlipkartDataReader(object):
    def __init__(self):
        self.usrIdToUsrDict = {}
        self.bnssIdToBnssDict = {}
        self.reviewIdToReviewDict = {}

    def readData(self, reviewFolder, readReviewsText=False):
        beforeDataReadTime = datetime.now()
        RATING_CSV_COLS = [REVIEW_ID, BNSS_ID, USER_ID, RATING, CREATE_TIMESTAMP]
        df1 = pandas.read_csv(os.path.join(reviewFolder, RATING_CSV),
                              escapechar='\\', skiprows=1, header=None, dtype=object, names=RATING_CSV_COLS)
        for tup in df1.itertuples():
            review_id, bnss_id, user_id, rating, creation_time_stamp, last_modified_time = tup
            review_id, bnss_id, user_id, rating, creation_time_stamp = \
                review_id, bnss_id, user_id, float(rating), datetime.datetime.strptime(creation_time_stamp, '%Y-%m-%d %H:%M:%S')

            if bnss_id not in self.bnssIdToBnssDict:
                self.bnssIdToBnssDict[bnss_id] = SIAUtil.business(bnss_id, bnss_id)
            bnss = self.bnssIdToBnssDict[bnss_id]

            if user_id not in self.usrIdToUsrDict:
                self.usrIdToUsrDict[user_id] = SIAUtil.user(user_id, user_id)
            usr = self.usrIdToUsrDict[user_id]

            revw = SIAUtil.review(review_id, usr.getId(), bnss.getId(), rating, creation_time_stamp)

            if review_id in self.reviewIdToReviewDict:
                print 'Already Read Meta - ReviewId:',review_id

            self.reviewIdToReviewDict[review_id] = revw

        print 'Users:', len(self.usrIdToUsrDict.keys()), \
            'Products:', len(self.bnssIdToBnssDict.keys()), \
            'Reviews:', len(self.reviewIdToReviewDict.keys())

        if not readReviewsText:
            return (self.usrIdToUsrDict, self.bnssIdToBnssDict, self.reviewIdToReviewDict)

        skippedData = 0
        df2 = pandas.read_csv(os.path.join(reviewFolder, REVIEW_CSV),
                              escapechar='\\', skiprows=1, header=None, dtype=object, names=REVIEW_CSV_COLS)
        for tup in df1.itertuples():
            review_id, bnss_id, user_id, generic_rating,\
            review_text, vertical, last_modified_time,\
            creation_time_stamp, first_to_review, certififed_buyer = tup

            if review_id in self.reviewIdToReviewDict:
                review_text = str(review_text)
                self.reviewIdToReviewDict[review_id].setReviewText(review_text)
            else:
                skippedData += 1

        afterDataReadTime = datetime.now()

        print 'Data Read Time:',(afterDataReadTime - beforeDataReadTime)
        print 'Skipped Count:', skippedData

        print 'Users:',len(self.usrIdToUsrDict.keys()), \
            'Products:',len(self.bnssIdToBnssDict.keys()), \
            'Reviews:',len(self.reviewIdToReviewDict.keys())

        textLessReviewId = set([review_id for review_id in self.reviewIdToReviewDict \
                                if not self.reviewIdToReviewDict[review_id].getReviewText()])
        for review_id in textLessReviewId:
            del self.reviewIdToReviewDict[review_id]
        print 'Removing text less reviews'

        print 'Users:', len(self.usrIdToUsrDict.keys()), \
            'Products:', len(self.bnssIdToBnssDict.keys()), \
            'Reviews:', len(self.reviewIdToReviewDict.keys())

        return (self.usrIdToUsrDict, self.bnssIdToBnssDict, self.reviewIdToReviewDict)
