# 1. 租用一个最新的 Java 21 运行环境 (鸡)
FROM eclipse-temurin:21-jdk-jammy

# 2. 设置在“集装箱”里的工作目录
WORKDIR /app

# 3. 把你刚写的配置和项目文件拷贝到集装箱里
COPY . .

# 4. 在集装箱内赋予 Gradle 执行权限 (仅针对 Linux/Mac 用户，建议保留以防万一)
RUN chmod +x gradlew || true

# 5. 告诉集装箱：启动时，请运行 Spring Boot 项目
# (这里我们先用命令行的形式启动)
CMD ["./gradlew", "bootRun"]
