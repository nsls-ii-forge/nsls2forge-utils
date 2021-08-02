OVERVIEW (8/1/21)
- This program creates a excel spreadsheet using Openpyxl, BeautifulSoup, and httplib2. The program uses a list of feedstock names generated from "https://nsls-ii-forge.github.io/docs/utils.html#all-feedstocks"
as long as the names.txt file is up to date the program will pull the all the current packages versions from the nsls-ii-forge and conda-forge channel.
Using the same names.txt file it will retrieve the feedstock URLS and the anaconda.org URLS.
BUGS (8/1/21)
- In the xlsheet-data.py the "get_versions" function sometimes throws a "List out of range" error, this is because if will sometimes recive a "request timeout" error.
Can usually be fixed by simply rerunning the program and making sure to have a stable connection.

- The xlsheet_data.py function "get_URLS" works by comparing the web codes retrieved through httplib2 requests. It does not download the entire webpage,
it only retrieves the 'HEAD' of the website. Some of the conda-forge feedstocks throw a webcode over 400 even though they do exist and the program marks
them "no feedstock exists". The feedstocks that do not get picked up are random, there does not seem to be an issue with the anaconda URLS.
