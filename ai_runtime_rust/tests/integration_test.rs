use ai_runtime::{AiRuntime, ExecutionBackend, PixelProgramRequest};
use serial_test::serial;
use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use gvpie_core::{PixelInstruction, PixelOp};
use tower::ServiceExt; // for `oneshot`


#[tokio::test]
#[serial]
async fn test_runtime_initialization() {
    let temp_dir = tempfile::tempdir().unwrap();
    std::env::set_var("GVPIE_CARTRIDGE_PATH", temp_dir.path());
    std::env::set_var("GVPIE_DISABLE_GPU", "1");
    let runtime = AiRuntime::new().await;
    assert!(runtime.is_ok());
}

#[tokio::test]
#[serial]
async fn test_gpu_detection() {
    let temp_dir = tempfile::tempdir().unwrap();
    std::env::set_var("GVPIE_CARTRIDGE_PATH", temp_dir.path());
    std::env::set_var("GVPIE_DISABLE_GPU", "1");
    let runtime = AiRuntime::new().await.unwrap();
    // This will be false in CI without GPU, but that's OK
    println!("GPU available: {}", runtime.gpu_available());
}

#[tokio::test]
#[serial]
async fn test_cartridge_crud_operations() {
    let temp_dir = tempfile::tempdir().unwrap();
    std::env::set_var("GVPIE_CARTRIDGE_PATH", temp_dir.path());
    std::env::set_var("GVPIE_DISABLE_GPU", "1");
    
    let runtime = AiRuntime::new().await.unwrap();
    
    // Test creating a cartridge
    let new_cartridge = ai_runtime::cartridges::Cartridge {
        id: "test_crud".to_string(),
        name: "Test CRUD".to_string(),
        description: "Testing CRUD operations".to_string(),
        code: "test code".to_string(),
        version: "1.0.0".to_string(),
        author: Some("Test".to_string()),
        tags: vec!["test".to_string()],
    };
    
    let result = runtime.create_cartridge(new_cartridge.clone()).await;
    assert!(result.is_ok());
    
    // Verify it exists
    let cartridge = runtime.get_cartridge("test_crud").await;
    assert!(cartridge.is_some());
    assert_eq!(cartridge.unwrap().name, "Test CRUD");
    
    // Test updating
    let updated = ai_runtime::cartridges::Cartridge {
        id: "test_crud".to_string(),
        name: "Updated Test".to_string(),
        description: "Updated description".to_string(),
        code: "updated code".to_string(),
        version: "2.0.0".to_string(),
        author: Some("Test".to_string()),
        tags: vec!["test".to_string()],
    };
    
    let update_result = runtime.update_cartridge(updated).await;
    assert!(update_result.is_ok());
    
    // Test deletion
    let delete_result = runtime.delete_cartridge("test_crud").await;
    assert!(delete_result.is_ok());
    
    // Verify deletion
    let deleted = runtime.get_cartridge("test_crud").await;
    assert!(deleted.is_none());
}

#[tokio::test]
#[serial] 
async fn test_api_cartridge_management() {
    let temp_dir = tempfile::tempdir().unwrap();
    std::env::set_var("GVPIE_CARTRIDGE_PATH", temp_dir.path());
    std::env::set_var("GVPIE_DISABLE_GPU", "1");
    
    let runtime = AiRuntime::new().await.unwrap();
    let app = axum::Router::new()
        .merge(ai_runtime::api::ApiServer::router(std::sync::Arc::new(runtime)));
    
    // Test cartridge creation via API
    let create_request = serde_json::json!({
        "id": "api_test",
        "name": "API Test",
        "description": "Testing API creation",
        "code": "print('hello')"
    });    
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/cartridges")
                .header("Content-Type", "application/json")
                .body(Body::from(create_request.to_string()))
                .unwrap()
        )
        .await
        .unwrap();
    
    assert_eq!(response.status(), StatusCode::OK);
    
    // Test getting the created cartridge
    let response = app
        .clone()
        .oneshot(Request::builder().uri("/api/cartridges/api_test").body(Body::empty()).unwrap())
        .await
        .unwrap();
    
    assert_eq!(response.status(), StatusCode::OK);
}

#[tokio::test]
#[serial]
async fn test_gpu_execution_reporting() {
    let temp_dir = tempfile::tempdir().unwrap();
    std::env::set_var("GVPIE_CARTRIDGE_PATH", temp_dir.path());
    std::env::set_var("GVPIE_DISABLE_GPU", "1");
    
    let runtime = AiRuntime::new().await.unwrap();
    
    // Test execution reports glyph expansion status
    let result = runtime.execute_cartridge("hello_world", None).await.unwrap();
    
    // Should report whether glyph expansion occurred
    assert!(result.backend == "cpu" || result.backend == "gpu");
    // glyphs_expanded should be set appropriately
    assert!(!result.data.is_empty());
}

#[tokio::test]
#[serial]
async fn test_pixel_vm_cpu_execution() {
    let temp_dir = tempfile::tempdir().unwrap();
    std::env::set_var("GVPIE_CARTRIDGE_PATH", temp_dir.path());
    std::env::set_var("GVPIE_DISABLE_GPU", "1");

    let runtime = AiRuntime::new().await.unwrap();

    let program = vec![
        PixelInstruction::new(PixelOp::SET as u8, 10, 42, 0),
        PixelInstruction::new(PixelOp::SET as u8, 11, 13, 0),
        PixelInstruction::new(PixelOp::HALT as u8, 0, 0, 0),
    ];

    let request = PixelProgramRequest {
        program: program.clone(),
        backend: ExecutionBackend::Cpu,
        max_cycles: 100,
        canvas_width: 8,
        canvas_height: 8,
    };

    let response = runtime.execute_pixel_program(request).await.unwrap();
    assert!(response.success);
    assert_eq!(response.backend_used, "cpu");
    assert_eq!(response.canvas_data[40], 42);
    assert_eq!(response.canvas_data[44], 13);
}

#[tokio::test]
#[serial]
async fn test_api_pixel_execute() {
    let temp_dir = tempfile::tempdir().unwrap();
    std::env::set_var("GVPIE_CARTRIDGE_PATH", temp_dir.path());
    std::env::set_var("GVPIE_DISABLE_GPU", "1");

    let runtime = AiRuntime::new().await.unwrap();
    let app = ai_runtime::api::ApiServer::router(std::sync::Arc::new(runtime));

    let program = vec![
        PixelInstruction::new(PixelOp::SET as u8, 5, 200, 0),
        PixelInstruction::new(PixelOp::HALT as u8, 0, 0, 0),
    ];

    let payload = serde_json::to_string(&serde_json::json!({
        "program": program,
        "backend": "cpu",
        "max_cycles": 50,
        "canvas_width": 8,
        "canvas_height": 8
    }))
    .unwrap();

    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/pixel/run")
                .header("Content-Type", "application/json")
                .body(Body::from(payload))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let bytes = hyper::body::to_bytes(response.into_body()).await.unwrap();
    let body: ai_runtime::PixelProgramResponse = serde_json::from_slice(&bytes).unwrap();
    assert!(body.success);
    assert_eq!(body.backend_used, "cpu");
}
