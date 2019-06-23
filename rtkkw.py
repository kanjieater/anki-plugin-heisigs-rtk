#
# Copyright: Robert Polz <robert.polz.cz@gmail.com>
# Batch-mode optimized by Vempele
# Vocab, links, override, maintenacne: KanjiEater
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Automatic RTK keyword generation.
#

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QAction

from anki.hooks import addHook
from aqt import mw
from aqt.utils import showInfo
from anki.utils import stripHTML
import re 

srcFields = ['Reading']
dstFields = ['Keywords']
rtkModel = 'Japanese Writing'
rtkKanjiField = 'Kanji'
rtkKeywordField = 'Heisig Keyword'
vocabField = 'KanjiVocabAnswer'
kanjiUrl = 'http://kanji.koohii.com/study/kanji/'
vocabUrl= 'https://jisho.org/search/'
OVERRIDE = True # Regenerate over existing content. USE WITH CAUTION!
# getKeywords
##########################################################################
cache = {}

def getMessage(note):
    kanji = note[rtkKanjiField]
    keyword = note[rtkKeywordField]
    message = "<a title='{}' href='{}{}'>{} - {}</a><br>".format(keyword, kanjiUrl, kanji, kanji, keyword)
    if note[vocabField]:
        search_string = re.sub("\[.*?\]", '', stripHTML(note[vocabField]))
        message = "<a title='{}' href='{}{}'>{} - {}</a><br>".format(keyword, vocabUrl, search_string, kanji, note[vocabField])
    return message, kanji

def generateCache():
    global cache
    model = mw.col.models.byName(rtkModel)
    mf = "mid:" + str(model['id'])
    ids = mw.col.findNotes(mf)
    for id in ids:
        note = mw.col.getNote(id)
        (message, kanji) = getMessage(note)
        if kanji in cache:
            cache[kanji] += message
        else:
            cache[kanji]  = message

def getKeywordsFast(expression):
    kw = ""
    for e in expression:
        if e in cache:
            kw += cache[e]
    return kw

def getKeywords(expression):
    model = mw.col.models.byName(rtkModel)
    mf = "mid:" + str(model['id'])
    message = ""
    for e in expression:
        ef = rtkKanjiField + ":" + e
        f = mf + " " + ef
        ids = mw.col.findNotes(f)
        for id in ids:
            note = mw.col.getNote(id)
            (m, kanji) = getMessage(note)
            message += m
    return message

# Focus lost hook
##########################################################################

def onFocusLost(flag, n, fidx):
    src = None
    dst = None
    # have src and dst fields?
    for c, name in enumerate(mw.col.models.fieldNames(n.model())):
        for f in srcFields:
            if name == f:
                src = f
                srcIdx = c
        for f in dstFields:
            if name == f:
                dst = f
    if not src or not dst:
        return flag
    # dst field already filled?
    if n[dst]:
        return flag
    # event coming from src field?
    if fidx != srcIdx:
        return flag
    # grab source text
    srcTxt = mw.col.media.strip(n[src])
    if not srcTxt:
        return flag
    # update field
    try:
        n[dst] = getKeywords(srcTxt)
    except Exception as e:
        raise
    return True

# Bulk keywords
##########################################################################

def regenerateKeywords(nids):
    mw.checkpoint("Bulk-add RTK Keywords")
    mw.progress.start()
    for nid in nids:
        note = mw.col.getNote(nid)

        src = None
        for fld in srcFields:
            if fld in note:
                src = fld
                break
        if not src:
            # no src field
            continue
        dst = None
        for fld in dstFields:
            if fld in note:
                dst = fld
                break
        if not dst:
            # no dst field
            continue
        if note[dst] and not OVERRIDE:
            # already contains data, skip
            continue
        srcTxt = mw.col.media.strip(note[src])
        if not srcTxt.strip():
            continue
        try:
            note[dst] = getKeywordsFast(srcTxt)
        except Exception as e:
            raise
        note.flush()
    mw.progress.finish()
    mw.reset()

# Menu
##########################################################################

def setupMenu(browser):
    try:
        if cache == {}:
            generateCache()
        a = QAction("Bulk-add RTK Keywords", browser)
        a.triggered.connect(lambda: onRegenerate(browser))
        browser.form.menuEdit.addSeparator()
        browser.form.menuEdit.addAction(a)
    except Exception as e:
        showInfo('Failed to generate cache, does your model exist?')

def onRegenerate(browser):
    regenerateKeywords(browser.selectedNotes())

# Init
##########################################################################

# addHook('editFocusLost', onFocusLost) #sometimes it adds EEEEEEEEVerything
addHook("browser.setupMenus", setupMenu)
