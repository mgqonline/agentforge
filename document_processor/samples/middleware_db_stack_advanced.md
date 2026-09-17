# 中间件与数据库 - 进阶代码与性能调优实战

## 1. MySQL 性能优化：EXPLAIN 执行计划分析

当你发现一条 SQL 查询极慢时，必须使用 `EXPLAIN` 来查看 MySQL 的查询优化器是如何执行它的：

```sql
EXPLAIN SELECT id, title FROM articles WHERE category_id = 5 AND status = 'published' ORDER BY created_at DESC;
```

**核心字段解析**：
- `type`（连接类型）：判断查询性能的关键。从好到坏依次是：`system` > `const` (主键精确匹配) > `eq_ref` > `ref` (普通非唯一索引匹配) > `range` (范围扫描) > `index` (全索引树扫描) > `ALL` (全表扫描)。**如果发现是 ALL，必须马上加索引**。
- `possible_keys`：可能用到的索引。
- `key`：实际决定使用的索引。
- `Extra`：
  - `Using filesort`：极度危险，说明 MySQL 无法利用索引完成排序，只能在内存或磁盘中开辟一块空间进行排序，必须优化联合索引顺序。
  - `Using index`：完美，说明发生了**索引覆盖 (Covering Index)**，查询的字段直接在二级索引树里就找到了，无需回表。

## 2. Redis 分布式锁：Lua 脚本保证原子性

在高并发秒杀或定时任务防重复执行场景中，直接使用 Redis 的 `SETNX` 和 `EXPIRE` 命令如果被分为两步，中间宕机会导致死锁。

**完美实现：基于 Lua 脚本的加锁与解锁**

加锁指令（Redis 2.6.12 后原生支持）：
```bash
# NX 表示不存在才设置，EX 30 表示 30秒过期
SET my_lock "unique_thread_id_123" NX EX 30
```

解锁必须验证这把锁是不是自己加的（防止误删别人因为超时释放后新加的锁），这需要两步（GET 然后 DEL），必须用 Lua 脚本保证原子性：

```lua
-- unlock.lua
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
```

Java (Jedis) 调用示例：
```java
String script = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end";
jedis.eval(script, Collections.singletonList("my_lock"), Collections.singletonList("unique_thread_id_123"));
```

## 3. Protobuf (gRPC) 定义与跨语言生成实战

Protobuf 是基于强契约的。你需要先编写 `.proto` 定义文件：

```protobuf
syntax = "proto3";

// 生成 Java 代码的包名配置
option java_package = "com.company.api";
option java_outer_classname = "UserProto";

// 定义消息体
message UserRequest {
  int64 user_id = 1;
}

message UserResponse {
  int64 id = 1;
  string username = 2;
  string email = 3;
  // enum 枚举定义
  enum Status {
    UNKNOWN = 0;
    ACTIVE = 1;
    BANNED = 2;
  }
  Status status = 4;
}

// 定义 gRPC 服务接口
service UserService {
  rpc GetUser (UserRequest) returns (UserResponse);
}
```

**编译命令**（以 Java 为例）：
```bash
protoc -I=. --java_out=./src/main/java user.proto
```
执行后，Protoc 编译器会自动生成极度优化的 `UserProto.java` 实体类，自带 Builder 模式，且所有的序列化 (`toByteArray()`) 与反序列化 (`parseFrom()`) 方法底层全部采用二进制位移操作，比 Jackson 处理 JSON 快一个数量级！
