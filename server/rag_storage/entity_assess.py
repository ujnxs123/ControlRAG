import json
import os
print("当前工作目录:", os.getcwd()) 
# 读取 JSON 文件
input_file = './server/rag_storage/vdb_entities.json'  # 替换为你的 JSON 文件路径
output_file = './server/rag_storage/entity.txt'  # 输出的文本文件路径

# 打开 JSON 文件并加载数据
with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 提取所有 entity_name 的值
entity_names = [item['entity_name'].strip('"') for item in data['data']]

# 将 entity_name 写入文本文件
with open(output_file, 'w', encoding='utf-8') as f:
    for name in entity_names:
        f.write(name + '\n')

print(f"共提取了 {len(entity_names)} 个 entity_name，已保存到 {output_file}")