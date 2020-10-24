"""Reverso Conjugator (conjugator.reverso.net) API for Python"""

from collections import namedtuple
import json

from bs4 import BeautifulSoup
import requests

__all__ = ["ReversoContextAPI", "WordUsageExample", "Translation", "InflectedForm"]

HEADERS = {"User-Agent": "Mozilla/5.0",
           "Content-Type": "application/json; charset=UTF-8"
           }

import requests

cookies = {
    'didomi_token': 'eyJ1c2VyX2lkIjoiMTc1MWZkMjctZTI5OC02YjkzLTgwZDktNjIxZDM3ZDZlYmFkIiwiY3JlYXRlZCI6IjIwMjAtMTAtMTNUMDI6Mzg6MTEuMzY2WiIsInVwZGF0ZWQiOiIyMDIwLTEwLTEzVDAyOjM4OjExLjM2NloiLCJ2ZXJzaW9uIjpudWxsfQ==',
    'experiment_dictionary_di45FDujv': '0',
    'experiment_conjugator_Gun7PhmuZ': '0',
    'JSESSIONID': 'iqxup6UfNWluk_ewxqucahch.bst-web15',
    'CTXTNODEID': 'bstweb15',
    'reverso.net._conj_en': 'de',
}

headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:81.0) Gecko/20100101 Firefox/81.0',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.5',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Referer': 'https://conjugator.reverso.net/conjugation-german-verb-hast.html',
}

params = (
    ('source_text', 'haben'),
    ('source_lang', 'de'),
    ('target_lang', 'en'),
    ('npage', '1'),
    ('json', '10'),
    ('pos_reorder', '8'),
    ('callback', 'jsonpContextCallback'),
    ('_', '1603380927235'),
)


WordUsageExample = namedtuple("WordUsageExample",
                              ("text", "highlighted"))

Translation = namedtuple("Translation",
                         ("source_word", "translation", "frequency", "part_of_speech", "inflected_forms"))

InflectedForm = namedtuple("InflectedForm",
                           ("translation", "frequency"))


class ReversoContextAPI(object):
    """Class for Reverso Context API (https://voice.reverso.net/)

    Attributes:
        source_text
        target_text
        source_lang
        target_lang
        page_count
    
    Methods:
        get_translations()
        get_examples()

    """

    def __init__(self, source_text="пример", target_text="", source_lang="ru", target_lang="en"):
        self.__source_text, self.__target_text, self.__source_lang, self.__target_lang, self.__page_count = None, None, None, None, None
        self.source_text, self.target_text, self.source_lang, self.target_lang = source_text, target_text, source_lang, target_lang
        self.__update_data()
        
    def __update_data(self):
        self.__data = {
            "source_text": self.source_text,
            "target_text": self.target_text,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
        }
        self.__info_modified = True

    @property
    def page_count(self):
        if self.__info_modified:
            self.__page_count = requests.post("https://context.reverso.net/bst-query-service", headers=HEADERS,
                                          data=json.dumps(self.__data)).json()["npages"]
            self.__info_modified = False
        return self.__page_count

    @property
    def source_text(self):
        return self.__source_text

    @property
    def target_text(self):
        return self.__target_text

    @property
    def source_lang(self):
        return self.__source_lang

    @property
    def target_lang(self):
        return self.__target_lang
    
    @source_text.setter
    def source_text(self, value):
        assert isinstance(value, str), "source text must be a string"
        self.__source_text = value
        self.__update_data()

    @target_text.setter
    def target_text(self, value):
        assert isinstance(value, str), "target text must be a string"
        self.__target_text = value
        self.__update_data()

    # TODO: add deeper check (is specified language really available) instead of just checking is a string given.

    @source_lang.setter
    def source_lang(self, value):
        assert isinstance(value, str), "language code must be a string"
        self.__source_lang = value
        self.__update_data()

    @target_lang.setter
    def target_lang(self, value):
        assert isinstance(value, str), "language code must be a string"
        self.__target_lang = value
        self.__update_data()

    def __repr__(self):
        return "ReversoContextAPI({source_text!r}, {target_text!r}, {source_lang!r}, {target_lang!r})" \
            .format(**self.__data)

    def __eq__(self, other):
        if isinstance(other, ReversoContextAPI):
            return self.source_text == other.source_text \
                   and self.target_text == other.target_text \
                   and self.source_lang == other.source_lang \
                   and self.target_lang == other.target_lang
        return False

    def get_translations(self):
        """Yields all available translations for the word (on the website you can find it just before the examples).

        Yields:
             Translation namedtuples.

        """

        translations_json = requests.post("https://context.reverso.net/bst-query-service", headers=HEADERS,
                                          data=json.dumps(self.__data)).json()["dictionary_entry_list"]
        for translation in translations_json:
            yield Translation(self.__data["source_text"], translation["term"], translation["alignFreq"],
                              translation["pos"],
                              [InflectedForm(form["term"], form["alignFreq"]) for form in
                               translation["inflectedForms"]])

    def get_examples(self):
        """A generator that gets words' usage examples pairs from server pair by pair.

        Note:
            Don't try to get all usage examples at one time if there are more than 5 pages (see the page_count attribute). It
            may take a long time to complete because it will be necessary to connect to the server as many times as there are pages exist.
            Just get the usage examples one by one as they are being fetched.

        Yields:
            Tuples with two WordUsageExample namedtuples (for source and target text and highlighted indexes)

        """

        def find_highlighted_idxs(soup, tag="em"):
            """Finds indexes of the parts of the soup surrounded by a particular HTML tag
            relatively to the soup without the tag.

            Example:
                soup = BeautifulSoup("<em>This</em> is <em>a sample</em> string")
                tag = "em"
                Returns: [(0, 4), (8, 16)]

            Args:
                soup: The BeautifulSoup's soup.
                tag: The HTML tag, which surrounds the parts of the soup.

            Returns:
                  A list of the tuples, which contain start and end indexes of the soup parts,
                  surrounded by tags.

            """

            cur, idxs = 0, []
            for t in soup.find_all(text=True):
                if t.parent.name == tag:
                    idxs.append((cur, cur + len(t)))
                cur += len(t)
            return idxs

        for npage in range(1, self.page_count + 1):
            self.__data["npage"] = npage
            examples_json = requests.post("https://context.reverso.net/bst-query-service", headers=HEADERS,
                                          data=json.dumps(self.__data)).json()["list"]
            for word in examples_json:
                source = BeautifulSoup(word["s_text"], features="lxml")
                target = BeautifulSoup(word["t_text"], features="lxml")
                yield (WordUsageExample(source.text, find_highlighted_idxs(source)),
                       WordUsageExample(target.text, find_highlighted_idxs(target)))

if __name__ == "__main__":
    response = requests.post('https://context.reverso.net/bst-query-service', headers=headers, data=params)
    #response = requests.get('https://context.reverso.net/bst-query-service', headers=headers, params=params, cookies=cookies)
    print("done")