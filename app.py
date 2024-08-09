import gradio as gr
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os

# 商品リストの定義
product_list = [
    {'name': '商品A', 'price': 100},
    {'name': '商品B', 'price': 200},
    {'name': '商品C', 'price': 300},
]

# 会計IDを初期化
transaction_id = 1

def add_to_cart(cart, total, selected_product, quantity):
    price = next(product['price'] for product in product_list if product['name'] == selected_product)
    cart.append({'name': selected_product, 'price': price, 'quantity': quantity})
    total += price * quantity
    dropdown_update, total_output, cart_output = update_cart_display(cart, total)
    return cart, total, dropdown_update, total_output, cart_output

def remove_from_cart(cart, total, selected_cart_item):
    if selected_cart_item:
        for cart_item in cart:
            if f"{cart_item['name']} (x{cart_item['quantity']}): ¥{cart_item['price'] * cart_item['quantity']}" == selected_cart_item:
                total -= cart_item['price'] * cart_item['quantity']
                cart.remove(cart_item)
                break
    dropdown_update, total_output, cart_output = update_cart_display(cart, total)
    return cart, total, dropdown_update, total_output, cart_output

def update_cart_display(cart, total):
    cart_output = [f"{cart_item['name']} (x{cart_item['quantity']}): ¥{cart_item['price'] * cart_item['quantity']}" for cart_item in cart]
    total_output = f"合計金額: ¥{total:.0f}"
    return gr.update(choices=cart_output), total_output, "\n".join(cart_output)

def submit_payment(cart, total, payment):
    global transaction_id
    if payment < total:
        change_output = "支払い金額が不足しています。"
        dropdown_update, total_output, cart_output = update_cart_display(cart, total)
        return cart, total, dropdown_update, total_output, cart_output, change_output

    change = payment - total
    change_output = f"おつり: ¥{change:.0f}"
    record_sales(cart, total, payment, change)

    # リセット
    cart = []
    total = 0
    transaction_id += 1
    return cart, total, gr.update(choices=[]), "合計金額: ¥0", "", change_output

def record_sales(cart, total, payment, change):
    global transaction_id
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 商品ごとの詳細データ
    detailed_data = [{'会計ID': transaction_id, '商品': item['name'], '価格': item['price'], '個数': item['quantity'], '日時': timestamp} for item in cart]
    detailed_df = pd.DataFrame(detailed_data)

    # ファイルが存在しない場合はヘッダー付きで保存
    if not os.path.isfile('detailed_sales.csv'):
        detailed_df.to_csv('detailed_sales.csv', mode='w', header=True, index=False, encoding='utf-8-sig')
    else:
        detailed_df.to_csv('detailed_sales.csv', mode='a', header=False, index=False, encoding='utf-8-sig')
    
    # 会計ごとのサマリーデータ
    summary_data = {'会計ID': transaction_id, '総額': total, '支払金額': payment, 'おつり': change, '日時': timestamp}
    summary_df = pd.DataFrame([summary_data])

    if not os.path.isfile('summary_sales.csv'):
        summary_df.to_csv('summary_sales.csv', mode='w', header=True, index=False, encoding='utf-8-sig')
    else:
        summary_df.to_csv('summary_sales.csv', mode='a', header=False, index=False, encoding='utf-8-sig')

def generate_receipt(cart, total):
    global transaction_id
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    receipt = f"会計ID: {transaction_id}\n日時: {timestamp}\n\n"
    receipt += "\n".join([f"{cart_item['name']} (x{cart_item['quantity']}): ¥{cart_item['price'] * cart_item['quantity']:.0f}" for cart_item in cart])
    receipt += f"\n\n合計金額: ¥{total:.0f}\n"
    receipt += "\n".join([f"{cart_item['name']}: {cart_item['quantity']}個" for cart_item in cart])
    return receipt

def view_sales_summary():
    if not os.path.isfile('detailed_sales.csv'):
        return "売上データがありません。"

    df = pd.read_csv('detailed_sales.csv', encoding='utf-8-sig')

    # 平均単価の計算
    df['総額'] = df['価格'] * df['個数']
    average_price = df['総額'].sum() / df['個数'].sum()

    # 売れ筋商品を見つける
    best_selling_product = df.groupby('商品')['個数'].sum().idxmax()
    best_selling_quantity = df.groupby('商品')['個数'].sum().max()

    summary = f"平均単価: ¥{average_price:.2f}\n売れ筋商品: {best_selling_product} ({best_selling_quantity}個)"

    return summary

def view_sales_data():
    if not os.path.isfile('detailed_sales.csv'):
        return "売上データがありません。"

    df = pd.read_csv('detailed_sales.csv', encoding='utf-8-sig')
    return df.to_html()

# Gradioインターフェースの設定
with gr.Blocks() as demo:
    cart = gr.State([])
    total = gr.State(0)

    with gr.Tab("レジ"):
        with gr.Row():
            with gr.Column():
                product_dropdown = gr.Dropdown(choices=[product['name'] for product in product_list], label="商品")
                quantity_input = gr.Number(label="個数", value=1, precision=0)
                add_button = gr.Button("カートに追加")
                cart_dropdown = gr.Dropdown(choices=[], label="カートの中身")
                remove_button = gr.Button("カートから削除")
                total_output = gr.Textbox(label="合計金額")
                cart_output = gr.Textbox(label="カートの詳細", interactive=False)
            with gr.Column():
                payment_input = gr.Number(label="支払い金額 (円)")
                submit_button = gr.Button("支払い処理")
                change_output = gr.Textbox(label="おつり")
                receipt_output = gr.Textbox(label="レシート", interactive=False)

        add_button.click(add_to_cart, inputs=[cart, total, product_dropdown, quantity_input], outputs=[cart, total, cart_dropdown, total_output, cart_output])
        remove_button.click(remove_from_cart, inputs=[cart, total, cart_dropdown], outputs=[cart, total, cart_dropdown, total_output, cart_output])
        submit_button.click(submit_payment, inputs=[cart, total, payment_input], outputs=[cart, total, cart_dropdown, total_output, cart_output, change_output])
        submit_button.click(generate_receipt, inputs=[cart, total], outputs=receipt_output)

    with gr.Tab("売上データの可視化"):
        sales_summary_output = gr.Textbox(label="売上データの要約", interactive=False)
        summary_button = gr.Button("売上データの要約を表示")
        summary_button.click(view_sales_summary, outputs=sales_summary_output)

    with gr.Tab("売上データの閲覧"):
        sales_data_output = gr.HTML()
        view_button = gr.Button("売上データを表示")
        view_button.click(view_sales_data, outputs=sales_data_output)

demo.launch(share=True)