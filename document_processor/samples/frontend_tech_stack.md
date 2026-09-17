# 现代前端核心技术栈深度解析

## 1. 核心框架：Vue 2 vs Vue 3 vs React

### 1.1 Vue 2 (经典选项式 API)
- **响应式原理**：基于 `Object.defineProperty` 劫持对象的 getter 和 setter。由于该 API 的限制，Vue 2 无法直接监听到对象属性的添加/删除以及数组下标的直接修改，因此需要 `Vue.set()` 和特定的数组重写方法（如 `push`, `splice`）来弥补。
- **组件复用**：主要依赖 Mixin（混入），容易导致命名冲突和数据来源不清晰（"来源不明的 this"）。
- **生命周期**：`created`, `mounted`, `updated`, `destroyed` 等。

### 1.2 Vue 3 (组合式 API - Composition API)
- **响应式原理**：全面拥抱 ES6 的 `Proxy` 对象，能够直接拦截整个对象的所有操作（包括属性新增、删除、数组下标修改等），不仅性能提升，而且解决了 Vue 2 的响应式痛点。
- **核心 API**：
  - `ref()`：用于基本数据类型的响应式包装（底层通过 getter/setter 拦截 `value` 属性）。
  - `reactive()`：用于复杂对象/数组的响应式包装（底层使用 Proxy）。
- **组件复用**：引入 Composition API（`setup` 函数），通过提取可复用的逻辑函数（Composables/Hooks）彻底取代 Mixin，使得业务逻辑更加聚合，代码高内聚低耦合。

### 1.3 React (函数式与 Hooks)
- **核心思想**：UI = f(State)。React 强调单向数据流和不可变性（Immutability）。
- **Virtual DOM 与 Fiber 架构**：通过内存中的虚拟 DOM 树比对（Diff 算法）计算出最小的真实 DOM 操作。React 16 引入的 Fiber 架构实现了可中断的异步渲染，解决了复杂组件树导致主线程阻塞（掉帧）的问题。
- **Hooks**：自 React 16.8 引入。
  - `useState`：状态管理。
  - `useEffect`：处理副作用（网络请求、订阅等），通过依赖数组控制执行时机。
  - `useMemo` / `useCallback`：用于性能优化的缓存。

## 2. 状态管理：Pinia 
Pinia 是 Vue 的专属状态管理库，已被官方推荐用于替代 Vuex。
- **极致扁平化**：去除了 Vuex 中繁琐的 `mutations`，仅保留 `state`, `getters`, `actions`。
- **TypeScript 支持**：天生具备极其完美的 TS 类型推断，无需像 Vuex 那样编写复杂的类型包装。
- **Store 独立**：不需要单一的全局根 Store，模块化拆分极其清晰，支持动态挂载。

## 3. 构建工具：Vite vs Webpack

### 3.1 Webpack (老牌霸主)
- **原理**：基于 Bundle（打包）机制。无论模块是否被修改，启动时都会从入口文件开始，构建完整的依赖图，然后将所有模块打包（bundle）后再输出交给浏览器。随着项目变大，冷启动速度极慢。
- **核心**：Loader（处理非 JS 文件，如 sass-loader, vue-loader）和 Plugin（在生命周期钩子中注入自定义逻辑）。

### 3.2 Vite (下一代前端工具)
- **原理**：基于浏览器原生的 ES Modules (ESM)。在开发环境下（Dev Server），Vite **不打包**你的代码。当浏览器请求某个模块时，Vite 才在服务端按需编译并返回。
- **极速冷启动**：依赖预构建（Pre-bundling）使用 Esbuild（Go 语言编写），比基于 Node.js 的打包器快 10-100 倍。
- **生产环境**：生产环境依然使用 Rollup 进行打包，以获得最佳的代码分割（Code Splitting）和 Tree-shaking 效果。

## 4. 网络层：Axios
- **基于 Promise**：支持 async/await 的现代 HTTP 客户端。
- **拦截器 (Interceptors)**：
  - **请求拦截器**：常用于在所有请求的 Header 中注入 Token（`Authorization: Bearer XXX`），或者全局开启 Loading 动画。
  - **响应拦截器**：常用于统一处理后端返回的错误码（如 401 自动跳转登录页、统一 Toast 弹窗报错）。
- **取消请求**：支持基于 `AbortController` 终止未完成的 HTTP 请求（防抖或路由切换时）。

## 5. 样式体系：CSS 现代特性
- **Flexbox**：一维布局神器。主要属性 `justify-content` (主轴对齐), `align-items` (交叉轴对齐), `flex: 1` (分配剩余空间)。
- **CSS Grid**：二维网格布局，适用于复杂的后台面板与画廊排版。
- **BEM 规范**：`Block__Element--Modifier`，一种 CSS 命名规范（如 `button__icon--active`），用于避免全局样式污染。
- **CSS 预处理器**：Sass/Less，提供变量、嵌套、Mixin 等高级特性。
- **现代方案**：CSS Modules 或 Tailwind CSS（原子化 CSS，通过组合 className 快速实现样式，高度复用且不会导致 CSS 体积膨胀）。
