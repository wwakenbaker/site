FROM nginx

RUN rm /etc/nginx/nginx.conf /etc/nginx/conf.d/default.conf

COPY /client/static /client/static

COPY /client/nginx.conf /etc/nginx/nginx.conf