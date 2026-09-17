# 后端核心技术栈 (Java 生态) 深度解析

## 1. Java 语言进阶：反射 (Reflection)

### 1.1 反射的核心概念
Java 反射机制允许在**运行状态**中，对于任意一个类，都能够知道这个类的所有属性和方法；对于任意一个对象，都能够调用它的任意方法和属性。这种动态获取信息以及动态调用对象方法的功能称为 Java 语言的反射机制。

### 1.2 核心类 (java.lang.reflect)
- `Class`：类的类，用于获取类的元数据（如 `Class.forName("com.mysql.cj.jdbc.Driver")`）。
- `Field`：类的成员变量，可通过 `setAccessible(true)` 强行访问私有（private）属性。
- `Method`：类的方法，可通过 `invoke(obj, args)` 动态执行。
- `Constructor`：类的构造方法，用于动态实例化对象 `newInstance()`。

### 1.3 反射的实际应用
- **Spring IoC 容器**：读取 XML 或注解配置，通过反射机制动态实例化 Bean 并完成依赖注入（DI）。
- **动态代理 (Dynamic Proxy)**：基于 JDK 的 `Proxy` 类结合 `InvocationHandler`，利用反射拦截方法调用，实现 AOP（面向切面编程），如事务管理、权限校验。
- **ORM 框架**：MyBatis 利用反射将数据库查询结果的 ResultSet 动态映射到 Java 实体类的属性上。

## 2. 框架演进：Spring Boot 2 vs Spring Boot 3

### 2.1 Spring Boot 2.x
- **基础依赖**：基于 Spring Framework 5.x，要求 Java 8+。
- **Java EE 规范**：底层依赖传统的 Java EE 规范，包命名空间为 `javax.*`（例如 `javax.servlet.http.HttpServletRequest`、`javax.persistence.Entity`）。

### 2.2 Spring Boot 3.x (划时代的重大升级)
- **基础依赖**：基于 Spring Framework 6.x，**强依赖 Java 17 作为最低版本**。
- **包名大迁移 (Jakarta EE)**：由于 Oracle 的商标权问题，Java EE 移交给 Eclipse 基金会并更名为 Jakarta EE。Spring Boot 3 将所有 `javax.*` 替换为了 `jakarta.*`。**这是升级项目时最大的破坏性更新**（例如需要将 `javax.servlet` 全面替换为 `jakarta.servlet`）。
- **原生镜像支持 (Native Image)**：Spring Boot 3 深度集成了 GraalVM，支持 AOT（Ahead-Of-Time）预先编译技术。能够将 Java 应用编译为不需要 JVM 即可运行的独立机器码可执行文件。这使得 Spring Boot 应用的冷启动时间从数秒降至**毫秒级**，内存占用极度降低，完美适配云原生 Serverless 场景。

## 3. ORM 框架：MyBatis 深度解析

### 3.1 核心组件
- `SqlSessionFactoryBuilder`：读取 MyBatis 配置文件并创建工厂。
- `SqlSessionFactory`：用于生产 SqlSession，通常应用全局单例。
- `SqlSession`：一次数据库会话，非线程安全，必须在用完后关闭。
- `Mapper`：接口和 XML 映射文件结合，定义 SQL 操作。

### 3.2 动态 SQL 机制
MyBatis 最强大的特性之一，通过 XML 标签在运行时动态拼接 SQL：
- `<if test="title != null"> AND title = #{title} </if>`：条件判断。
- `<where>`：自动处理条件前多余的 `AND` 或 `OR`。
- `<foreach collection="list" item="id" open="(" separator="," close=")">`：用于遍历集合，通常用于批量插入或 `IN` 查询。

### 3.3 参数传递 (`#` 与 `$`)
- `#{}`：预编译处理（PreparedStatement），MyBatis 会将 SQL 中的 `#{}` 替换为 `?`，并使用参数注入，**能有效防止 SQL 注入攻击**，推荐日常查询必须使用。
- `${}`：字符串直接拼接。存在极高的 SQL 注入风险。但对于需要动态传递**表名、列名、或者排序规则（ORDER BY ${column} ASC）**的场景，只能使用 `${}`。

### 3.4 MyBatis 缓存机制
- **一级缓存 (Local Cache)**：SqlSession 级别的缓存，默认开启。同一个 SqlSession 下，相同的查询语句将直接从缓存中返回。执行 `INSERT`/`UPDATE`/`DELETE` 会清空一级缓存。
- **二级缓存 (Global Cache)**：Mapper Namespace 级别的缓存，跨 SqlSession 共享。需要手动在 XML 中配置 `<cache/>` 标签。由于在分布式环境下（多节点部署）极易造成数据脏读，现代微服务架构中**极其不推荐使用 MyBatis 的二级缓存**，而是由 Redis 接管全局分布式缓存。
