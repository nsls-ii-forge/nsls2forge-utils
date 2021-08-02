#!/usr/bin/env python
from bs4 import BeautifulSoup
from time import sleep
import requests
import warnings
import httplib2
warnings.filterwarnings('ignore', category = UserWarning) # supresses the MarkupResemblesLocatorWarning(UserWarning) message for bs4

def get_versions(namedata, URLv, filename):

    for i in range(len(namedata)):
        link = URLv + namedata[i].strip()
        html = BeautifulSoup(link, features = 'lxml')
        p = html.findAll('p')
        type(p)
        len(p)
        p0=p[0]
        r = requests.get(p0.text, timeout=100)
        svg = BeautifulSoup(r.text, features = 'lxml')
        version_tag = svg.findAll('text')[-1]

        with open(filename, 'a') as file:
            file.write(version_tag.text + '\n')

def get_URLS(namedata, URLn, filename, type):
    tag = httplib2.Http()

    for i in range(len(namedata)):
        if type == "feedstock":
            link = URLn + namedata[i].strip() + "-feedstock"
            print1 = "no feedstock exists"
            resp = tag.request(link, 'HEAD')

            if int(resp[0]['status']) < 400:
                with open(filename, 'a') as file:
                    file.write(link + '\n')
            else:
                with open(filename, 'a') as file:
                    file.write(print1 + '\n')
        else:
            link = URLn + namedata[i].strip()
            print1 = "no anaconda package exists"
            resp = tag.request(link, 'HEAD')

            if int(resp[0]['status']) > 200:
                with open(filename, 'a') as file:
                    file.write(link + '\n')
            else:
                with open(filename, 'a') as file:
                    file.write(print1 + '\n')

condaURLv = "https://img.shields.io/conda/vn/conda-forge/"
nsls2URLv = "https://img.shields.io/conda/vn/nsls2forge/"
condafilename = "conda-forge-vrs.txt"
nsls2filename = "nsls2forge-vrs.txt"

feedstockURL = "https://github.com/conda-forge/"
anacondaURL = "https://anaconda.org/conda-forge/"
feedstocksURLfilename = "feedstock-URLS.txt"
anacondaURLfilename = "anaconda-URLS.txt"

condafile = open("conda-forge-vrs.txt", 'w')
nsls2f = open("nsls2forge-vrs.txt", 'w')

git_URLS = open("feedstock-URLS.txt", 'w')
anaconda_URLS = open("anaconda-URLS.txt", 'w')

namedata = []
repos = open('names.txt', "r")
namedata = repos.readlines()

get_versions(namedata, condaURLv, condafilename)
get_versions(namedata, nsls2URLv, nsls2filename)

get_URLS(namedata, feedstockURL, feedstocksURLfilename, "feedstock")
get_URLS(namedata, anacondaURL, anacondaURLfilename, "anaconda")

# create excel spreadsheet
import xlsheet
