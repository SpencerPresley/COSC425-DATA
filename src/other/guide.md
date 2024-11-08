Have some crossref jsons 

do the following for each json object

<!-- 1) go through current json object and extract salisbury authors, if there are no salisbury authors, not a salisbury paper, throw away -->
2) go through current json object and extract abstract
3) pass the abstract to get categorized
4) get categoreis back, and insert them into the json object

do that for each json object then you have categories in all the json objects
run process as normal


categories for abstract

for each of those categories, create a categoryInfo object
parsing through the same json object pulling out salisbury authors, adding them in, pulling out departments, adding them in, pulling out citations adding em in, pulling out citation count adding them in. 

Say now go to next json object

abstract gets categorized into different categories, do the same thing, create a categoryInfo object, add in the salisbury authors, add in the departments, add in the citations, add in the citation count. 

Say now go to next json object
abstracts gets categorized into a category that already has some stuff, add all that info into the categoryInfo object.


=============================================================================================================

When start Wos_classification.py, it takes in a big ass wos record file, it splits these files into individual records, and slaps them in a directory. 

It goes over each file in there (each record) and does all that shit that i just wrote above.

=============================================================================================================
have all the json objects

we pass in the list of json objects, and perform the above steps.


