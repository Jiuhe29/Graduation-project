import requests
import os
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# API 和 目录配置
aircraft_api = "https://source.cengceng.chat/safe/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/84.0.4147.105 Safari/537.36"
}
proxies = {}

# 配置日期和文件夹
date = "2025-05-09"
img_dir = f"./Apple_images/{date}"
os.makedirs(img_dir, exist_ok=True)  # 创建目录

# 失败记录文件
progress_file = "Apple_progress.json"

# 线程锁（防止多线程修改共享数据）
lock = threading.Lock()

# 读取下载进度（成功 & 失败）
def load_progress():
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            data = json.load(f)
            return data.get("failed_images", []), data.get("success_images", {})
    return [], {}

# 保存下载进度（成功 & 失败）
def save_progress(failed_list, success_dict):
    with lock:
        with open(progress_file, 'w') as f:
            json.dump({"failed_images": failed_list, "success_images": success_dict}, f, indent=4)

# 清除失败记录
def clear_failed_records():
    if os.path.exists(progress_file):
        os.remove(progress_file)
        print("🗑️ 失败记录已清除！")
    else:
        print("⚠️ 没有发现失败记录文件！")

# 下载图片
def download_image(i, failed_list, success_dict):
    img_name = f"{date}-IMG_{i:04d}.jpeg"
    img_path = os.path.join(img_dir, img_name)

    # **检查 JSON 是否已有成功下载的记录**
    if img_name in success_dict:
        print(f"⏩ 跳过 {img_name}（已成功下载）")
        return True

    url = aircraft_api + img_name

    try:
        response = requests.get(url, headers=headers, proxies=proxies, timeout=10)

        if response.status_code == 200:
            with open(img_path, "wb") as f:
                f.write(response.content)

            img_size_mb = len(response.content) / (1024 * 1024)  # 转换为 MB
            print(f"✅ 图片 {img_name} 下载完成，大小: {img_size_mb:.2f} MB")

            with lock:
                success_dict[img_name] = img_size_mb  # 记录下载成功的图片
            return True  # 下载成功

        else:
            print(f"❌ 图片 {img_name} 不存在（{response.status_code}）")

    except requests.RequestException as e:
        print(f"⚠️ 请求异常：{img_name}，错误：{e}")
        with lock:
            failed_list.append(img_name)  # 追加失败的图片名称

    save_progress(failed_list, success_dict)  # 更新失败 & 成功记录

# 并行下载
def download_images_in_parallel(max_workers=20):
    failed_list, success_dict = load_progress()  # 读取下载记录
    start, end = 1, 10000  # 预设下载范围

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_img = {executor.submit(download_image, i, failed_list, success_dict): i for i in range(start, end)}

        for future in as_completed(future_to_img):
            future.result()

    # 记录失败的任务
    if failed_list:
        save_progress(failed_list, success_dict)
        print(f"\n⚠️ 共有 {len(failed_list)} 张图片请求异常，已记录到 {progress_file}")

    summarize_downloads(success_dict)  # 输出成功下载的统计信息

# 输出下载成功的文件名与大小
def summarize_downloads(success_dict):
    if not success_dict:
        print("\n⚠️ 没有成功下载的图片。")
        return

    total_size = sum(success_dict.values())

    print("\n✅ 下载完成的文件列表：")
    for img_name, img_size_mb in success_dict.items():
        print(f"  - {img_name}（{img_size_mb:.2f} MB）")

    print(f"\n📊 共下载成功 {len(success_dict)} 个文件，总大小：{total_size:.2f} MB\n")

# 失败任务重试
def retry_failed_downloads(max_retries=3):
    failed_list, success_dict = load_progress()

    for attempt in range(1, max_retries + 1):
        if not failed_list:
            print("\n✅ 所有失败的图片已成功下载！")
            menu()  # **返回主菜单**
            return

        print(f"\n🔄 开始第 {attempt} 轮重试，{len(failed_list)} 张图片...")

        new_failed_list = []

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_img = {
                executor.submit(download_image, int(img_name.split("_")[-1].split(".")[0]), new_failed_list, success_dict): img_name
                for img_name in failed_list
            }

            for future in as_completed(future_to_img):
                future.result()

        with lock:
            failed_list[:] = new_failed_list  # 更新失败列表
            save_progress(failed_list, success_dict)  # 保存最新的失败 & 成功记录

        summarize_downloads(success_dict)  # 输出成功下载的统计信息

    if failed_list:
        print(f"\n🚨 仍有 {len(failed_list)} 张图片下载失败（可能是 404），程序继续运行...")
    else:
        print("\n🎉✅ 所有失败图片重试成功！")

    menu()  # **返回菜单，防止程序退出**

# 交互式菜单
def menu():
    while True:
        print("\n📌 请选择操作：")
        print("1️⃣  开始批量下载图片 (1~10000)")
        print("2️⃣  重新下载失败任务")
        print("3️⃣  清除失败记录")
        print("4️⃣  退出")

        choice = input("👉 请输入选项 (1/2/3/4)：").strip()

        if choice == "1":
            download_images_in_parallel()

        elif choice == "2":
            retry_failed_downloads()

        elif choice == "3":
            clear_failed_records()

        elif choice == "4":
            print("👋 退出程序，再见！")
            break

        else:
            print("⚠️ 请输入有效选项！")

# 主程序入口
if __name__ == "__main__":
    try:
        menu()
    except KeyboardInterrupt:
        print("\n⚠️ 任务被中断，进度已保存。")