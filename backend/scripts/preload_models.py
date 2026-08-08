from vector_store import preload_models

if __name__ == '__main__':
    print('[preload_models] Preloading embedding models...')
    preload_models()
    print('[preload_models] Done.')
