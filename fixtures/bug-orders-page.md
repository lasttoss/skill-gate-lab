# Bug report

`GET /orders?page=2&size=20` returns 19 rows. Expected 20.
Suspected slice with an exclusive end index.
