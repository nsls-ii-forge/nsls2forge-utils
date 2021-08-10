#!/usr/bin/env python
import yaml
from bs4 import BeautifulSoup
import requests
import warnings

warnings.filterwarnings("ignore", category=UserWarning)
# supresses the MarkupResemblesLocatorWarning(UserWarning) message for bs4


def get_versions(namedata, URLv, set):

    for i in range(len(namedata)):
        link = URLv + namedata[i].strip()
        html = BeautifulSoup(link, features="lxml")
        p = html.findAll("p")
        type(p)
        len(p)
        p0 = p[0]
        r = requests.get(p0.text, timeout=100)
        svg = BeautifulSoup(r.text, features="lxml")
        version_tag = svg.findAll("text")[-1]

        if set == "conda":
            datadict["package" + str(i)] = {
                "package_name": namedata[i].strip(),
                "conda_version": version_tag.text,
                "nsls2_version": 0,
                "feedstock_URL": 0,
                "anaconda_URL": 0,
            }
        else:
            datadict["package" + str(i)]["nsls2_version"] = version_tag.text


def get_urls(namedata, URLn, type):

    for i in range(len(namedata)):
        if type == "feedstock":
            link = URLn + namedata[i].strip() + "-feedstock"
            print1 = "no feedstock exists"
            response = requests.get(link)
            if response:
                datadict["package" + str(i)]["feedstock_URL"] = link
            else:
                datadict["package" + str(i)]["feedstock_URL"] = print1
        else:
            link = URLn + namedata[i].strip()
            print1 = "no anaconda package exists"
            response = requests.head(link)
            if response.status_code > 302:
                datadict["package" + str(i)]["anaconda_URL"] = link
            else:
                datadict["package" + str(i)]["anaconda_URL"] = print1


condaURLv = "https://img.shields.io/conda/vn/conda-forge/"
nsls2URLv = "https://img.shields.io/conda/vn/nsls2forge/"
feedstockURL = "https://github.com/conda-forge/"
anacondaURL = "https://anaconda.org/conda-forge/"

namedata = []
repos = open("names.txt", "r")
namedata = repos.readlines()

datadict = {}  # data dictionary

get_versions(namedata, condaURLv, "conda")
get_versions(namedata, nsls2URLv, "nsls2")

get_urls(namedata, feedstockURL, "feedstock")
get_urls(namedata, anacondaURL, "anaconda")

with open("xldata.yml", "w") as fp:  # dumps datadict into a yaml file
    data = yaml.dump(datadict, fp)

# create excel spreadsheet
import xlsheet
