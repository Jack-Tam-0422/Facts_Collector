# Jinja2 template for Nginx config

Mappings/dicts are transformed into Nginx blocks. You can nest dicts to nest blocks. The macro will recurse through the nested dicts.
```yaml
http:
  server:
    location /: {}
    location /api: {}
```
```
http {
    server {
        location / {
        }
        location /api {
        }
    }
}
```


To define multiple blocks with the same name (e.g multiple `server` blocks), use lists. Like:
```yaml
server:
  -
    parameter: value
  - 
    parameter2: value2
```
which becomes:
```
server {
    parameter value;
}
server {
    parameter2 value2;
```


A list of parameters (i.e. not dicts) of length `n` is transformed into `n` instances of the parameter. E.g.
```yaml
listen:
  - 80
  - '[::]:80'
```
becomes
```
listen 80;
listen [::]:80;
```


Boolean values are translated to `on` or `off` as appropriate
```yaml
access_log: false
log_not_found: true
```
```
access_log off;
log_not_found on;
```


Ben Crisp <ben@thecrisp.io>