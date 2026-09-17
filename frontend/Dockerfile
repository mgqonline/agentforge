# ========== Stage 1: Build React Frontend ==========
FROM node:20-alpine AS build-react
WORKDIR /app/frontend-react
COPY frontend-react/package*.json ./
RUN npm config set registry https://registry.npmmirror.com && npm install
COPY frontend-react ./
RUN npm run build

# ========== Stage 2: Build Vanilla Frontend ==========
FROM node:20-alpine AS build-vanilla
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm config set registry https://registry.npmmirror.com && npm install
COPY frontend ./
# 将 base 路径指定为 /vanilla/，保证部署在子路径下的静态资源加载正常
RUN npx vite build --base=/vanilla/

# ========== Stage 3: Runtime Nginx Image ==========
FROM nginx:alpine

# 移除默认的静态页面与配置
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/default.conf

# 部署两个前端工程构建产物
COPY --from=build-react /app/frontend-react/dist /usr/share/nginx/html/react
COPY --from=build-vanilla /app/frontend/dist /usr/share/nginx/html/vanilla

# 复制 Nginx 反向代理与路由配置
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
