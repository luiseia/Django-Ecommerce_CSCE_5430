# ShopProject — Django E-commerce

## 项目结构
- config/          → 项目设置、根 URL、WSGI/ASGI
- accounts/        → 自定义 User 模型、认证、个人资料
- products/        → 商品和分类模型
- orders/          → 订单和订单项模型
- cart/            → 购物车模型
- templates/       → 所有 HTML 模板 (Bootstrap 5)
- static/          → CSS、JS、图片

## 技术栈
- Django 5.2 LTS
- 自定义 User 模型，email 登录
- 三个角色：Shopper, Merchant, Administrator
- Bootstrap 5 响应式模板

## 命令
- `python manage.py runserver` — 启动开发服务器
- `python manage.py makemigrations` — 生成迁移
- `python manage.py migrate` — 执行迁移
- `python manage.py seed_products` — 填充测试数据

## 当前需要实现的功能

### 1. Personal Page（个人页面）
用户可以查看和编辑自己的个人信息（姓名、邮箱、电话、头像等）。
每个用户都有一个专属的个人页面展示他们的信息。

### 2. Bookmarks（收藏夹）
用户可以将商品添加到收藏夹，方便以后查看。
需要创建 Bookmark 模型、添加/删除收藏的视图和模板。