.. _endpoint_name:

Notifications
=============

An endpoint to get Notifications.

**URL**: /api/notifications

**Methods**: GET.

**Request Args**: limit-The limit number of notifications.

**Response**: Returns latest notifications.

**Example request**:

**/api/notifications?limit=5**

**Example response**:

.. code-block:: json

    [
      "time_created":"29/12/2023 22",
      "message":"Irrigation started",
      "id":23,
      "category":"notices"
    ]

.. .. automodule:: models
..    :members: