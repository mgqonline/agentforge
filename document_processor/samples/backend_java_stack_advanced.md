# 后端核心技术栈 (Java 生态) - 进阶代码与实战指南

## 1. Java 反射 (Reflection) 动态代理实战

反射最典型的场景是在 AOP（面向切面编程）中，通过动态代理在方法执行前后插入逻辑（如计算耗时、事务提交）：

```java
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

interface UserService {
    void saveUser();
}

class UserServiceImpl implements UserService {
    public void saveUser() {
        System.out.println("User saved to database.");
    }
}

// 动态代理处理器
class TimingInvocationHandler implements InvocationHandler {
    private final Object target;

    public TimingInvocationHandler(Object target) {
        this.target = target;
    }

    @Override
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
        long start = System.currentTimeMillis();
        // 利用反射动态调用目标对象的方法
        Object result = method.invoke(target, args);
        long end = System.currentTimeMillis();
        System.out.println(method.getName() + " executed in " + (end - start) + "ms");
        return result;
    }
}

public class Main {
    public static void main(String[] args) {
        UserService target = new UserServiceImpl();
        UserService proxyInstance = (UserService) Proxy.newProxyInstance(
            target.getClass().getClassLoader(),
            target.getClass().getInterfaces(),
            new TimingInvocationHandler(target)
        );
        // 调用时，将先走 invoke 方法打印耗时
        proxyInstance.saveUser();
    }
}
```

## 2. Spring Boot 3 AOT 原生镜像 (GraalVM) 实战

Spring Boot 3 支持将应用编译为操作系统直接可执行的二进制文件。在 `pom.xml` 中只需引入 `native-maven-plugin`：

```xml
<build>
    <plugins>
        <plugin>
            <groupId>org.graalvm.buildtools</groupId>
            <artifactId>native-maven-plugin</artifactId>
            <configuration>
                <!-- 配置原生镜像参数 -->
                <buildArgs>
                    <buildArg>-H:+ReportExceptionStackTraces</buildArg>
                    <buildArg>--no-fallback</buildArg>
                </buildArgs>
            </configuration>
        </plugin>
        <plugin>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-maven-plugin</artifactId>
        </plugin>
    </plugins>
</build>
```
打包命令：`mvn -Pnative native:compile`。生成的二进制文件无需 JRE 环境，启动时间从 1500ms 直接暴降至 30ms，完美适配 K8s 容器极速扩容。

## 3. MyBatis 高阶动态 SQL 实战

在企业级 CRUD 中，我们经常需要处理包含多个可选搜索条件的查询，MyBatis 的 `<where>` 和 `<if>` 完美解决了 `1=1` 的蹩脚拼接：

```xml
<!-- UserMapper.xml -->
<mapper namespace="com.example.mapper.UserMapper">
    
    <select id="searchUsers" resultType="com.example.entity.User">
        SELECT id, username, email, status, created_at 
        FROM sys_user
        <where>
            <!-- 自动去掉多余的 AND -->
            <if test="username != null and username != ''">
                AND username LIKE CONCAT('%', #{username}, '%')
            </if>
            <if test="status != null">
                AND status = #{status}
            </if>
            <if test="roleIds != null and roleIds.size() > 0">
                AND role_id IN
                <!-- 遍历集合构建 IN 子句 -->
                <foreach item="roleId" collection="roleIds" open="(" separator="," close=")">
                    #{roleId}
                </foreach>
            </if>
        </where>
        <!-- 使用 ${} 动态传递排序列名，必须在 Java 层做白名单校验防注入 -->
        ORDER BY ${orderByColumn} DESC
    </select>

</mapper>
```
