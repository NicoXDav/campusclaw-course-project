"""Warm the real embedding model outside web-worker startup timeouts."""
import os
if os.getenv('EMBEDDING_PROVIDER','local') == 'local':
    from fastembed import TextEmbedding
    model=TextEmbedding(os.getenv('EMBEDDING_MODEL','BAAI/bge-small-zh-v1.5'),
        cache_dir=os.getenv('MODEL_CACHE','data/models'),threads=2)
    vector=next(iter(model.embed(['知识库检索预热'])))
    print(f'真实嵌入模型已就绪，维度 {len(vector)}。')
else:
    print('当前使用嵌入网关，无需本地模型缓存。')
