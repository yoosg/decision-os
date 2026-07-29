allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}
// 플러그인 서브프로젝트(예: app_settings)가 낮은 compileSdk(33)로 빌드되어
// 최신 AndroidX(fragment 1.7.1 등, compileSdk 34+ 요구)와 충돌하는 문제 해결.
// AGP 버전 간 API 차이에 견고하도록 리플렉션으로 compileSdk를 36으로 강제.
// evaluationDependsOn(":app")가 서브프로젝트를 평가하기 전에 afterEvaluate를 등록해야 하므로
// 반드시 그 블록보다 먼저 위치시킨다("already evaluated" 오류 방지).
subprojects {
    afterEvaluate {
        val android = extensions.findByName("android") ?: return@afterEvaluate
        val cls = android.javaClass
        runCatching {
            cls.methods.first { it.name == "setCompileSdk" && it.parameterCount == 1 }
                .invoke(android, 36)
        }.recoverCatching {
            cls.methods.first {
                it.name == "setCompileSdkVersion" &&
                    it.parameterCount == 1 &&
                    it.parameterTypes[0] == Int::class.javaPrimitiveType
            }.invoke(android, 36)
        }
    }
}
subprojects {
    project.evaluationDependsOn(":app")
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
