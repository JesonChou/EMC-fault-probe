import json


def search_json_by_string_enhanced(file_path, search_string, target_field=None):
    """
    在JSON文件中搜索包含特定字符串的词条（增强版）

    Args:
        file_path (str): JSON文件路径
        search_string (str): 要搜索的字符串
        target_field (str, optional): 指定搜索的字段名，如果为None则搜索所有字段

    Returns:
        list: 包含搜索字符串的词条列表
    """
    try:
        # 1. 读取JSON文件
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        # 2. 筛选包含搜索字符串的词条
        results = []
        for item in data:
            if target_field:
                # 只在指定字段中搜索
                if target_field in item and isinstance(item[target_field], str):
                    if search_string in item[target_field]:
                        results.append(item)
            else:
                # 在所有字段中搜索
                for value in item.values():
                    if isinstance(value, str) and search_string in value:
                        results.append(item)
                        break

        return results

    except FileNotFoundError:
        print(f"错误：文件 '{file_path}' 未找到")
        return []
    except json.JSONDecodeError:
        print(f"错误：文件 '{file_path}' 不是有效的JSON格式")
        return []
    except Exception as e:
        print(f"发生错误：{e}")
        return []


# 使用示例
if __name__ == "__main__":
    file_path = "dataStore.json"

    # 示例1：在所有字段中搜索
    search_text = "传导发射与辐射发射超标"
    print(f"搜索字符串: '{search_text}'")
    print("=" * 80)

    matched_entries = search_json_by_string_enhanced(file_path, search_text)
    print(f"找到 {len(matched_entries)} 条匹配结果\n")

    # 示例2：只在"故障现象"字段中搜索
    print(f"在'故障现象'字段中搜索: '{search_text}'")
    print("=" * 80)

    matched_entries_field = search_json_by_string_enhanced(
        file_path, search_text, target_field="故障现象"
    )
    print(f"找到 {len(matched_entries_field)} 条匹配结果\n")

    # 显示详细结果
    for i, entry in enumerate(matched_entries, 1):
        print(f"匹配结果 {i}:")
        print(f"  故障对象: {entry.get('故障对象', 'N/A')}")
        print(f"  故障现象: {entry.get('故障现象', 'N/A')[:100]}...")  # 只显示前100个字符
        print()