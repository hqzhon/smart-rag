# 向量数据库垃圾数据清理脚本使用说明

## 概述

`cleanup_orphaned_vectors.py` 是一个用于清理向量数据库中垃圾数据的脚本。它会识别并删除在 `documents` 表中不存在对应记录的向量数据，确保向量数据库与关系数据库的数据一致性。

## 垃圾数据定义

垃圾数据是指向量数据库中存在，但在 MySQL `documents` 表中没有对应 `document_id` 记录的数据。这种情况通常发生在：

1. 文档被从 `documents` 表中删除，但向量数据未同步删除
2. 向量化过程中出现异常，导致部分数据残留
3. 系统异常中断导致的数据不一致

## 功能特性

- **安全的试运行模式**：默认为试运行模式，不会实际删除数据
- **详细的统计信息**：显示总chunks数、孤立chunks数、孤立文档数等
- **分批删除**：避免一次性删除大量数据造成系统负载
- **完整的日志记录**：记录详细的操作过程和结果
- **多种运行模式**：支持统计、试运行、强制执行等模式

## 使用方法

### 1. 查看帮助信息

```bash
python scripts/cleanup_orphaned_vectors.py --help
```

### 2. 仅查看统计信息（推荐首次使用）

```bash
python scripts/cleanup_orphaned_vectors.py --stats-only
```

输出示例：
```
=== 向量数据库统计信息 ===
总chunks数: 513
孤立chunks数: 491
孤立文档数: 43
孤立文档ID列表: ['15e53307-5e8d-4745-a48c-4cc07faee229', ...]
```

### 3. 试运行模式（默认，安全）

```bash
python scripts/cleanup_orphaned_vectors.py --dry-run
```

或者简单地：
```bash
python scripts/cleanup_orphaned_vectors.py
```

这会显示将要删除的数据，但不会实际执行删除操作。

### 4. 强制执行删除（谨慎使用）

```bash
python scripts/cleanup_orphaned_vectors.py --force
```

**注意**：这会实际删除孤立的向量数据，操作不可逆！系统会要求输入 'YES' 进行二次确认。

### 5. 调整日志级别

```bash
python scripts/cleanup_orphaned_vectors.py --log-level DEBUG --stats-only
```

支持的日志级别：DEBUG, INFO, WARNING, ERROR

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--dry-run` | 试运行模式，不实际删除数据 | True |
| `--force` | 强制执行删除操作 | False |
| `--stats-only` | 仅显示统计信息，不执行清理 | False |
| `--log-level` | 设置日志级别 | INFO |

## 安全建议

1. **首次使用前**：先运行 `--stats-only` 查看统计信息
2. **测试运行**：使用默认的试运行模式查看将要删除的数据
3. **备份数据**：在执行实际删除前，建议备份向量数据库
4. **分批执行**：如果孤立数据量很大，脚本会自动分批删除（每批100个）
5. **监控日志**：注意观察执行过程中的日志信息

## 执行流程

1. **初始化**：连接 MySQL 数据库和向量数据库
2. **获取有效文档ID**：从 `documents` 表获取所有有效的文档ID
3. **扫描向量数据**：获取向量数据库中所有数据的元数据
4. **识别孤立数据**：找出在 `documents` 表中不存在的 `document_id`
5. **执行清理**：根据运行模式决定是否实际删除数据

## 输出结果

脚本执行完成后会显示清理结果：

```
=== 清理结果 ===
执行成功: True
发现孤立chunks: 491
删除chunks: 491  # 试运行模式下为0
执行时间: 2.35秒
```

## 错误处理

- **数据库连接失败**：检查数据库配置和网络连接
- **向量存储未初始化**：确保 ChromaDB 正常运行
- **权限不足**：确保有足够的数据库操作权限
- **内存不足**：对于大量数据，脚本会自动分批处理

## 注意事项

1. **不可逆操作**：使用 `--force` 参数删除的数据无法恢复
2. **性能影响**：清理大量数据时可能对系统性能有短暂影响
3. **并发安全**：避免在文档上传或处理过程中执行清理操作
4. **定期维护**：建议定期运行此脚本维护数据一致性

## 故障排除

### 常见问题

1. **ImportError**: 确保所有依赖包已安装
2. **数据库连接超时**: 检查网络和数据库服务状态
3. **权限错误**: 确保数据库用户有足够权限
4. **内存不足**: 对于大型数据库，考虑增加系统内存

### 日志分析

脚本会输出详细的日志信息，包括：
- 数据库连接状态
- 扫描进度
- 删除操作结果
- 错误信息和堆栈跟踪

## 示例使用场景

### 场景1：定期维护
```bash
# 每周检查一次数据一致性
python scripts/cleanup_orphaned_vectors.py --stats-only

# 如果发现孤立数据，先试运行
python scripts/cleanup_orphaned_vectors.py --dry-run

# 确认无误后执行清理
python scripts/cleanup_orphaned_vectors.py --force
```

### 场景2：系统迁移后清理
```bash
# 系统迁移或数据导入后，清理可能的不一致数据
python scripts/cleanup_orphaned_vectors.py --force
```

### 场景3：调试模式
```bash
# 详细调试信息
python scripts/cleanup_orphaned_vectors.py --log-level DEBUG --stats-only
```

## 相关文件

- `app/storage/database.py`: 数据库操作接口
- `app/storage/vector_store.py`: 向量存储操作接口
- `scripts/cleanup_vector_db.py`: 另一个清理脚本（功能类似）

## 版本历史

- v1.0: 初始版本，支持基本的孤立数据清理功能