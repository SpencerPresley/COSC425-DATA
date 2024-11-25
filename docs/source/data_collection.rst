data\_collection package
========================

Submodules
----------

data\_collection.CrossrefWrapper module
---------------------------------------

.. automodule:: academic_metrics.data_collection.CrossrefWrapper
   :members:
   :no-index:
   :undoc-members:
   :show-inheritance:

data\_collection.scraper module
-------------------------------

.. automodule:: academic_metrics.data_collection.scraper
   :members:
   :no-index:
   :undoc-members:
   :show-inheritance:data\_collection package
========================

Module Constants
---------------
.. py:data:: CROSSREF_API_URL
   :type: str
   
   Base URL for the Crossref API.

.. py:data:: CROSSREF_WORKS_URL
   :type: str
   
   URL for accessing works in the Crossref API.

Classes
--------

CrossrefWrapper
~~~~~~~~~~~~~~
.. py:class:: CrossrefWrapper

   Wrapper class for interacting with the Crossref API.

   .. py:method:: get_works(query: str) -> List[Dict]
      
      Retrieves works from Crossref matching the query.

Scraper
~~~~~~~
.. py:class:: Scraper

   Class for scraping academic data.

Module contents
---------------

.. automodule:: academic_metrics.data_collection
   :members:
   :undoc-members:
   :show-inheritance: