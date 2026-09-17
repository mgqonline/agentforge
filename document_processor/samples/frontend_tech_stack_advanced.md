# 现代前端核心技术栈 - 进阶代码与实战指南

## 1. Vue 3 (Composition API) vs React (Hooks) 核心代码对比

### 1.1 组件状态与副作用管理
**Vue 3 (`<script setup>` 语法糖)**:
```html
<script setup>
import { ref, onMounted, watch } from 'vue'

const count = ref(0)
const data = ref(null)

// 监听器
watch(count, async (newVal) => {
  console.log(`Count changed to ${newVal}`)
})

// 生命周期钩子 (副作用)
onMounted(async () => {
  const res = await fetch('/api/init')
  data.value = await res.json()
})
</script>

<template>
  <button @click="count++">Clicked {{ count }} times</button>
</template>
```

**React (Functional Component)**:
```jsx
import React, { useState, useEffect } from 'react';

export default function Counter() {
  const [count, setCount] = useState(0);
  const [data, setData] = useState(null);

  // 副作用与监听器结合 (依赖数组为 [] 相当于 onMounted)
  useEffect(() => {
    const fetchData = async () => {
      const res = await fetch('/api/init');
      setData(await res.json());
    };
    fetchData();
  }, []);

  // 依赖数组包含 count，当 count 变化时触发
  useEffect(() => {
    console.log(`Count changed to ${count}`);
  }, [count]);

  return (
    <button onClick={() => setCount(c => c + 1)}>
      Clicked {count} times
    </button>
  );
}
```

## 2. 生产级 Axios 拦截器 (无感刷新 Token 实战)

在企业级前端应用中，处理 JWT Token 的自动刷新是拦截器的经典应用：

```javascript
import axios from 'axios';

const api = axios.create({ baseURL: 'https://api.example.com' });
let isRefreshing = false;
let requestsQueue = [];

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    // 如果返回 401 且未重试过
    if (error.response.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // 正在刷新时，将其他请求排队挂起
        return new Promise((resolve) => {
          requestsQueue.push((token) => {
            originalRequest.headers['Authorization'] = 'Bearer ' + token;
            resolve(api(originalRequest));
          });
        });
      }
      originalRequest._retry = true;
      isRefreshing = true;
      try {
        const { data } = await axios.post('/auth/refresh_token');
        const newToken = data.token;
        localStorage.setItem('token', newToken);
        api.defaults.headers.common['Authorization'] = 'Bearer ' + newToken;
        
        // 执行队列中的挂起请求
        requestsQueue.forEach(cb => cb(newToken));
        requestsQueue = [];
        return api(originalRequest);
      } catch (refreshError) {
        // 刷新失败，强制退回登录页
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);
export default api;
```

## 3. Vite 极速构建配置实战

Vite 通过配置 `vite.config.ts` 可以轻松实现跨域代理与路径别名，而无需像 Webpack 那样编写繁琐的 loader。

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    port: 3000,
    open: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
```
