│   app.md （本文件,税明整个项目的目录结构及文件归属,是指导AI完成开发的重要框架性帮助文件)）
│   main.py （整个程序的主入口，采用tornado架构构建实现，MVC三层经典架构）
│   test.py （程序单元测试用脚本文件,主要用于模块/包/方法的测试,可以写入一些临时性的测试用例)）
│  
├───app （整个项目的主包)）
│   │   *init*.py
│   │  
│   ├───controllers （MVC中的控制层模块）
│   │   │   auth.py （鉴权有关的控制层方法,涉及登录、注册、退出）
│   │   │   base.py  （）
│   │   │   home.py （）
│   │   │   *init*.py
│   │   │  
│   │   └───\_\_pycache\_\_
│   │           auth.cpython-311.pyc
│   │           base.cpython-311.pyc
│   │           home.cpython-311.pyc
│   │  
│   ├───models （业务与数据模型层）
│   │   │   db.py （sqlite数据库访问层【model】，后续可以在此拓展兼容mysql/pgsq|等数据库访问逻辑）
│   │   │   user.py (对应用户相关的madel)
│   │   │   *init*.py
│   │   │  
│   │   └───\_\_pycache\_\_
│   │           db.cpython-311.pyc
│   │           user.cpython-311.pyc
│   │  
│   ├───static (view中的静态资源)
│   │   ├───css (样式)
│   │   │       base.css （基础公共样式）
│   │   │  
│   │   └───js （JS脚本）
│   │           base.js （基础公共脚本）
│   │  
│   └───templates （view试图）
│           base.html （基础模板）
│           index.html （后台首页模板）
│           login.html （登录页模板）
│           register.html （注册页模板）
│  
├───database （sqlite数据库目录）
│       app.db （当前自动创建的sqlite数据库，通过init\_db()在启动时检查创建）
│  
└───venv （python3.11 下创建的venv看见，语法：python -m venv venv）


