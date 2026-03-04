import os
import requests
from pystac_client import Client


def download_sentinel2_data():
    print("=== Sentinel-2 L2A 地质遥感数据下载工具 (AWS) ===")

    # 1. 获取用户输入的矿权区坐标
    print("\n请输入矿权区域的边界坐标 (Bounding Box)，格式为: 最小经度,最小纬度,最大经度,最大纬度")
    print("例如: 116.3, 39.8, 116.5, 40.0")
    bbox_input = input("坐标: ")
    bbox = [float(x.strip()) for x in bbox_input.split(',')]

    # 2. 获取时间范围
    date_range = input("\n请输入时间范围 (格式 YYYY-MM-DD/YYYY-MM-DD，例如 2023-01-01/2023-12-31): ")

    # 3. 获取云量要求
    max_cloud = input("\n请输入最大云量百分比 (建议地质解译 < 20): ")

    print("\n正在通过 STAC API 检索 AWS 上的 Sentinel-2 L2A 数据...")

    # 连接到 Element 84 Earth Search (索引了 AWS 上的 Sentinel-2 数据)
    catalog = Client.open("https://earth-search.aws.element84.com/v1")

    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=date_range,
        query={"eo:cloud_cover": {"lt": float(max_cloud)}}
    )

    items = list(search.items())
    print(f"共找到 {len(items)} 景符合条件的影像。")

    if len(items) == 0:
        print("未找到符合条件的影像，请尝试扩大时间范围或放宽云量限制。")
        return

    # 取云量最少的一景作为示例下载
    best_item = min(items, key=lambda item: item.properties.get("eo:cloud_cover", 100))
    print(f"\n选择云量最优的影像: {best_item.id} (云量: {best_item.properties['eo:cloud_cover']}%)")

    # 地质勘探核心波段提取：
    # B02, B03, B04 (可见光 - 真彩色基底)
    # B08 (近红外 - 植被掩膜)
    # B11, B12 (短波红外 SWIR - 提取泥化、绢云母化等含水硅酸盐矿物)
    target_bands = ['blue', 'green', 'red', 'nir', 'swir16', 'swir22']

    download_dir = f"./{best_item.id}"
    os.makedirs(download_dir, exist_ok=True)

    for band in target_bands:
        if band in best_item.assets:
            asset = best_item.assets[band]
            url = asset.href
            # 处理部分返回 s3:// 协议的情况
            if url.startswith("s3://"):
                url = url.replace("s3://sentinel-cogs/", "https://sentinel-cogs.s3.us-west-2.amazonaws.com/")

            print(f"正在下载波段 {band}: {url}")
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                file_path = os.path.join(download_dir, f"{band}.tif")
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"波段 {band} 下载完成。")
            else:
                print(f"下载失败: HTTP {response.status_code}")

    print(f"\n下载流程结束。数据保存在: {os.path.abspath(download_dir)}")


if __name__ == "__main__":
    download_sentinel2_data()