use ai_runtime::{AiRuntime, ApiServer};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt()
        .with_target(false)
        .init();

    tracing::info!("Starting AI Runtime");

    let runtime = AiRuntime::new().await
        .map_err(|e| Box::new(e) as Box<dyn std::error::Error>)?;
    let server = ApiServer::new(runtime);

    tracing::info!("Listening on http://0.0.0.0:8080");
    server.run("0.0.0.0:8080").await?;
    Ok(())
}
