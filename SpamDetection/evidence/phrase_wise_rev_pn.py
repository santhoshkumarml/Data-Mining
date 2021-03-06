'''
Created on Dec 30, 2015

@author: santhosh
'''
import os
from wordcloud.wordcloud import WordCloud, STOPWORDS

import matplotlib.pyplot as plt
from util import PlotUtil


POS_REVW_FILE = 'pos_reviews'
NEG_REVW_FILE = 'neg_reviews'
ALL_REVIEWS_FILE = 'all_reviews'

def plotWordCloud(revws, title, imgFolder):
    imgFile = os.path.join(imgFolder, title + '.png')
    # Generate a word cloud image
    text = ' '.join([revw.getReviewText() for revw in revws])

    wordcloud = WordCloud(max_font_size=40, relative_scaling=.5,
                          stopwords=STOPWORDS).generate(text)
    plt.figure(figsize=(20, 20))
    plt.imshow(wordcloud)
    plt.axis("off")
    plt.title(title)
    plt.tight_layout()
    PlotUtil.savePlot(imgFile, isPdf=False)

def writeReviewTextInFile(reviews, review_file_name, fdr):
    log_file = os.path.join(fdr, review_file_name + '.txt')
    print 'Logging in Log File', log_file
    with open(log_file, 'w') as f:
        for revw in reviews:
            f.write(revw.getReviewText())
            f.write('\n')
    if len(reviews) > 0:
        plotWordCloud(reviews, review_file_name, fdr)

def runPhraseFilterAndSeperate(reviews, phrases, fdr):
    filtered_reviews =[]
    for phrase in phrases:
        for revw in reviews:
            if phrase.lower() in revw.getReviewText().lower():
                filtered_reviews.append(revw)
    pos_filtered_reviews = [revw for revw in filtered_reviews if revw.getRating()>=4.0]
    neg_filtered_reviews = [revw for revw in filtered_reviews if revw.getRating()<=2.0]
    print '-----------------------------------------------'
    print phrases
    for r in filtered_reviews:
        print r.getReviewText()
    print '-----------------------------------------------'
    writeReviewTextInFile(filtered_reviews, ALL_REVIEWS_FILE, fdr)
    writeReviewTextInFile(pos_filtered_reviews, POS_REVW_FILE, fdr)
    writeReviewTextInFile(neg_filtered_reviews, NEG_REVW_FILE, fdr)


def runOnAllReviews(reviews, fdr):
    pos_reviews = [revw for revw in reviews if revw.getRating()>=4.0]
    neg_reviews = [revw for revw in reviews if revw.getRating()<=2.0]

    writeReviewTextInFile(reviews, ALL_REVIEWS_FILE, fdr)
    writeReviewTextInFile(pos_reviews, POS_REVW_FILE, fdr)
    writeReviewTextInFile(neg_reviews, NEG_REVW_FILE, fdr)