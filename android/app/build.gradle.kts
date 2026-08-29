import java.util.Properties

plugins {
    id("com.android.application")
}

// Signing details live in keystore.properties next to this project. If it is
// missing the build falls back to the debug key so a clone still builds.
val signingProps = Properties().apply {
    val file = rootProject.file("keystore.properties")
    if (file.exists()) {
        file.inputStream().use { load(it) }
    }
}
val hasSigningKey = signingProps.getProperty("storeFile")
    ?.let { rootProject.file(it).exists() } == true

android {
    namespace = "com.chillbot.panel"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.chillbot.panel"
        minSdk = 26
        targetSdk = 34
        versionCode = 2
        versionName = "1.1"
    }

    if (hasSigningKey) {
        signingConfigs {
            create("app") {
                storeFile = rootProject.file(signingProps.getProperty("storeFile"))
                storePassword = signingProps.getProperty("storePassword")
                keyAlias = signingProps.getProperty("keyAlias")
                keyPassword = signingProps.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = if (hasSigningKey) {
                signingConfigs.getByName("app")
            } else {
                signingConfigs.getByName("debug")
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

/** Drops the finished apk in android/dist/ under a friendly name. */
tasks.register<Copy>("apk") {
    dependsOn("assembleRelease")
    from(layout.buildDirectory.file("outputs/apk/release/app-release.apk"))
    into(rootProject.file("dist"))
    rename { "chillbot-panel.apk" }
}
