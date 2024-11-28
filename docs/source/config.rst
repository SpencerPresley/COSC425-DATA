Global Configuration
======================

Overview
----------
.. automodule:: academic_metrics.configs.global_config
   :no-members:

Module Constants
-----------------
.. py:data:: LOG_TO_CONSOLE
   :type: bool
   
   Controls whether log messages are displayed in the console. Default is True.

.. py:data:: LOG_LEVEL
   :type: int

   Sets the default logging level. Default is DEBUG.

.. py:data:: DEBUG
   :type: int
.. py:data:: INFO
   :type: int
.. py:data:: WARNING
   :type: int
.. py:data:: ERROR
   :type: int
.. py:data:: CRITICAL
   :type: int

   Log level constants exported for use across the package.

Classes
---------

Color Formatter
~~~~~~~~~~~~~~~~
.. autoclass:: academic_metrics.configs.global_config.ColorFormatter
   :members:
   :undoc-members:
   :show-inheritance:
   :private-members:
   :special-members: __init__

Functions
-----------

Configure Logging
~~~~~~~~~~~~~~~~~~
.. autofunction:: academic_metrics.configs.global_config.configure_logging

Set Log to Console
~~~~~~~~~~~~~~~~~~~
.. autofunction:: academic_metrics.configs.global_config.set_log_to_console
