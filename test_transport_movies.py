#rm movie*mrcs ; scipion python test_transport_movies.py
import sqlite3
from sqlite3 import Error
import time
from random import randint
from os import remove, getenv
from os.path import join
import glob
lastMovieDeleted =0
FACTOR=1.0
NUMBERHOLES = 128
NUMBERMOVIESPERHOLE = 4
TIMEPERMOVIE = int(20 * FACTOR) # secs # 5
TIMEMOVEHOLE = int(44 * FACTOR) # secs # 10
FAILURERATE = 75 # 1 = all holes, slip 1 each 4 times

DATABASENAME = 'movies.sqlite'
TABLENAMEMOVIES = 'movies'
TABLENAMEHOLES = 'holes'

LARGEON = False

if LARGEON:
    INMOVIENAME = '22_large_4bit.mrcs'
else:
    INMOVIENAME = '../Data/22_4bit.mrcs'

scipionUserData = getenv('SCIPION_USER_DATA')
PROJECT='bench'
PROTOCOLDIR='011477_ProtMotionCorr/'
EXTRA='extra'


def createDataBase(databasename):
    DROPTABLECOMMAND = "DROP TABLE IF EXISTS {tablename}"
    CREATETABLEHOLESCOMMAND="""
    CREATE TABLE {tablename}(
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       startCreateAt INTEGER DEFAULT -1,
       spentTime INTEGER DEFAULT -1
    );"""

    CREATETABLEMOVIESCOMMAND="""
    CREATE TABLE {tablename}(
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       movieName text,
       holeId INTEGER REFERENCES {tablenameHole}(id),
       startCreateAt INTEGER DEFAULT -1,
       spentTime INTEGER DEFAULT -1,
       toBeDeleted INTEGER DEFAULT 0,
       alreadyDeleted INTEGER DEFAULT 0
    );
    """

    CREATEINDEXCOMMAND="""CREATE INDEX {indexname} ON
    {tablename}({attributename});"""

    try:
        conn = sqlite3.connect(databasename)
        cur = conn.cursor()
        cur.execute(DROPTABLECOMMAND.format(tablename=TABLENAMEMOVIES))
        cur.execute(DROPTABLECOMMAND.format(tablename=TABLENAMEHOLES))
        cur.execute(CREATETABLEHOLESCOMMAND.format(
            tablename=TABLENAMEHOLES))
        sqlCommand = CREATETABLEMOVIESCOMMAND.format(
            tablename=TABLENAMEMOVIES, tablenameHole=TABLENAMEHOLES)
        cur.execute(sqlCommand)
        attributename = 'toBeDeleted'
        indexname = "%s_%s"%(TABLENAMEMOVIES, attributename)
        sqlCommand = CREATEINDEXCOMMAND.format(indexname=indexname,
                                               tablename=TABLENAMEMOVIES,
                                               attributename=attributename)
        cur.execute(sqlCommand)
        attributename = 'alreadyDeleted'
        indexname = "%s_%s"%(TABLENAMEMOVIES, attributename)
        sqlCommand = CREATEINDEXCOMMAND.format(indexname=indexname,
                                               tablename=TABLENAMEMOVIES,
                                               attributename=attributename)
        cur.execute(sqlCommand)
        return cur, conn
    except Error as e:
        print(e)
        exit(0)

def readImage(inFileName):
    with open(inFileName, 'r') as f:
        contents=f.read()
    return contents

def writeImage(outFileName, contents):
    with open(outFileName, 'w') as f:
        f.write(contents)

def createImage(ih, outFileName):
    ih.write(outFileName)

def deleteUsedMovies(cur):
    global lastMovieDeleted
    doneString = 'DONE_movie_*.TXT'
    deleteCounter = 0
    _path = join(scipionUserData,'projects', PROJECT,'Runs', PROTOCOLDIR, EXTRA, doneString)
    number = 0
    print "_path", _path
    for file in sorted(glob.glob(_path)):
        end = file.split('DONE_movie_')[1]
        number = int(end.split('.')[0])
        if number > lastMovieDeleted:
            cur.execute("""SELECT movieName
                           FROM {tablename}
                           WHERE id={movId}""".format(
                tablename=TABLENAMEMOVIES, movId=number))
            row = cur.fetchone()
            try:
                print "removing: ", row[0]
                remove(row[0])
            except:
                print "could not remove file"

            deleteCounter += 1
    lastMovieDeleted = number
    return deleteCounter

    # #  get list of movies to be deleted
    # cur.execute("""SELECT id, movieName
    #                FROM {tablename}
    #                WHERE toBeDeleted=1
    #                  AND alreadyDeleted=0""".format(
    #     tablename=TABLENAMEMOVIES))
    # rows = cur.fetchall()
    #
    # # delete movies
    # for row in rows:
    #     movieFileName = row[1]
    #     print "remove file %s" % movieFileName
    #     remove(movieFileName)
    #
    # # update database
    # if len(rows) > 0:
    #     sqlCommand = """UPDATE {tablename}
    #                    set alreadyDeleted = 1
    #                    WHERE id=?""".format(tablename=TABLENAMEMOVIES)
    #     data = [(row[0],) for row in rows]
    #     cur.executemany(sqlCommand, data)
    #     conn.commit()
    # # return number of deleted movies
    # return len(rows)

def insertHole(cur, conn, startDate):
    attribute = 'startCreateAt'
    INSERTCOMMAND="""INSERT INTO {tablename} ({attribute})
    VALUES ({startDate})""".format(tablename=TABLENAMEHOLES,
                                   attribute=attribute,
                                   startDate=startDate)
    cur.execute(INSERTCOMMAND)
    id = cur.lastrowid
    conn.commit()
    return id

def updateHole(cur, conn, holeId, spentTime):
    attribute = 'spentTime'
    UPDATECOMMAND = """UPDATE {tablename} set {attribute} = {spentTime}
    WHERE id={holeId}""".format(tablename=TABLENAMEHOLES,
                                attribute=attribute,
                                spentTime=spentTime,
                                holeId=holeId)

    cur.execute(UPDATECOMMAND)
    conn.commit()


def insertMovie(cur, conn, movieName, startDate, spentTime, holeId):

    attributes = 'movieName, holeId, startCreateAt, spentTime'
    values = "'{movieName}', {holeId}, {startDate}, {spentTime}".format(
        movieName=movieName, holeId=holeId, startDate=startDate,
        spentTime=spentTime
    )
    INSERTCOMMAND = """INSERT INTO {tablename} ({attributes})
    VALUES ({values})""".format(tablename=TABLENAMEMOVIES,
                                   attributes=attributes,
                                   values=values)
    cur.execute(INSERTCOMMAND)
    id = cur.lastrowid
    conn.commit()
    return id

# create database
cur, conn = createDataBase(DATABASENAME)

# load image in memory
contents = readImage(INMOVIENAME)
#DEBUG: writeImage('kk.mrcs', contents)

# loop that creates streaming
for hole in range(NUMBERHOLES):
    #  record hole start in database
    startHole = time.time()
    holeId = insertHole(cur, conn, startHole)
    print "holeId", holeId
    # should I skip this hole?
    randNum = randint(0, 99)
    if randNum >= FAILURERATE:
        print "skipping hole", holeId, "randNum =", randNum
    else:
        for movie in range(NUMBERMOVIESPERHOLE):
            startMovie = time.time()
            outFileName = "movie_{hole}_{movie}.mrcs".format(
                 hole=holeId, movie=movie+1)
            #  record movie
            writeImage(outFileName, contents)
            endMovie = time.time()
            #  record movie end in database
            timeSpendMovie = endMovie - startMovie
            print "finishing movie: ", movie +1 , timeSpendMovie
            if timeSpendMovie < TIMEPERMOVIE:
                print "sleeping: ", TIMEPERMOVIE - timeSpendMovie
                time.sleep(TIMEPERMOVIE - timeSpendMovie)
            # record movie
            movieId = insertMovie(cur, conn, outFileName,
                                  startMovie, timeSpendMovie, holeId)
    endHole = time.time()
    timeSpendHole = endHole - startHole
    updateHole(cur, conn, holeId, timeSpendHole)
    print "finishing hole: ", holeId, timeSpendHole
    startDelete = time.time()
    numDeleted = deleteUsedMovies(cur)
    endDelete = time.time()
    # # substract time spend deleting movies
    print "movies deleted = ", numDeleted
    print "hole extra wait", (TIMEMOVEHOLE - (endDelete - startDelete))
    time.sleep(TIMEMOVEHOLE - (endDelete - startDelete))
