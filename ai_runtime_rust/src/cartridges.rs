use serde::{Deserialize, Serialize};
use std::{
    collections::HashMap,
    fs,
    path::{Path, PathBuf},
};
use thiserror::Error;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Cartridge {
    pub id: String,
    pub name: String,
    pub description: String,
    pub code: String,
    pub version: String,
    pub author: Option<String>,
    pub tags: Vec<String>,
}

#[derive(Debug, Error)]
pub enum CartridgeError {
    #[error("cartridge not found: {0}")]
    NotFound(String),
    #[error("filesystem error: {0}")]
    Io(#[from] std::io::Error),
    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

#[derive(Debug)]
pub struct CartridgeManager {
    cartridges: HashMap<String, Cartridge>,
    storage_root: PathBuf,
}

impl CartridgeManager {
    pub fn new<P: AsRef<Path>>(storage_root: P) -> Result<Self, CartridgeError> {
        let storage_root = storage_root.as_ref().to_path_buf();
        let mut manager = Self {
            cartridges: HashMap::new(),
            storage_root,
        };
        manager.load_or_initialize()?;
        Ok(manager)
    }

    pub fn list(&self) -> Vec<Cartridge> {
        self.cartridges.values().cloned().collect()
    }

    pub fn get(&self, id: &str) -> Option<Cartridge> {
        self.cartridges.get(id).cloned()
    }

    pub fn execute(
        &self,
        id: &str,
        input: Option<&str>,
    ) -> Result<Vec<u8>, CartridgeError> {
        let cartridge = self
            .cartridges
            .get(id)
            .ok_or_else(|| CartridgeError::NotFound(id.to_string()))?;

        tracing::info!(
            "Executing cartridge id={} name={} input_len={:?}",
            cartridge.id,
            cartridge.name,
            input.map(|s| s.len())
        );

        Ok(cartridge.code.as_bytes().to_vec())
    }

    pub fn create_cartridge(&mut self, cartridge: Cartridge) -> Result<(), CartridgeError> {
        if self.cartridges.contains_key(&cartridge.id) {
            return Err(CartridgeError::NotFound(format!("Cartridge already exists: {}", cartridge.id)));
        }
        
        self.save_cartridge(&cartridge)?;
        self.cartridges.insert(cartridge.id.clone(), cartridge.clone());
        println!("📦 Created new cartridge: {}", cartridge.id);
        Ok(())
    }
    
    pub fn update_cartridge(&mut self, cartridge: Cartridge) -> Result<(), CartridgeError> {
        if !self.cartridges.contains_key(&cartridge.id) {
            return Err(CartridgeError::NotFound(cartridge.id));
        }
        
        self.save_cartridge(&cartridge)?;
        self.cartridges.insert(cartridge.id.clone(), cartridge.clone());
        println!("📦 Updated cartridge: {}", cartridge.id);
        Ok(())
    }
    
    pub fn delete_cartridge(&mut self, id: &str) -> Result<(), CartridgeError> {
        let path = Path::new(&self.storage_root).join(format!("{}.json", id));
        if path.exists() {
            fs::remove_file(path)?;
        }
        
        self.cartridges.remove(id);
        println!("🗑️ Deleted cartridge: {}", id);
        Ok(())
    }

    fn load_or_initialize(&mut self) -> Result<(), CartridgeError> {
        if !self.storage_root.exists() {
            fs::create_dir_all(&self.storage_root)?;
            self.write_default_cartridges()?;
        }

        let mut loaded_any = false;

        for entry in fs::read_dir(&self.storage_root)? {
            let entry = entry?;
            let path = entry.path();
            if path.extension().and_then(|ext| ext.to_str()) != Some("json") {
                continue;
            }

            let content = fs::read_to_string(&path)?;
            if content.trim().is_empty() {
                continue;
            }

            let cartridge: Cartridge = serde_json::from_str(&content)?;
            self.cartridges.insert(cartridge.id.clone(), cartridge);
            loaded_any = true;
        }

        if !loaded_any {
            self.write_default_cartridges()?;
            // Recursive call will populate cartridges from freshly written files.
            self.load_or_initialize()?;
        }

        Ok(())
    }

    fn write_default_cartridges(&mut self) -> Result<(), CartridgeError> {
        let defaults = vec![
            Cartridge {
                id: "hello_world".to_string(),
                name: "Hello World".to_string(),
                description: "Basic greeting cartridge demonstrating text output".to_string(),
                code: "print(\"Hello, Sovereign AI!\")".to_string(),
                version: "1.0.0".to_string(),
                author: Some("system".to_string()),
                tags: vec!["demo".to_string(), "basic".to_string()],
            },
            Cartridge {
                id: "matrix_display".to_string(),
                name: "Matrix Display".to_string(),
                description: "Generates ASCII rain for the glyph expander".to_string(),
                code: "generate_matrix_rain(128, 64)".to_string(),
                version: "1.0.0".to_string(),
                author: Some("system".to_string()),
                tags: vec!["display".to_string(), "demo".to_string()],
            },
            Cartridge {
                id: "glyph_expander".to_string(),
                name: "Glyph Expander".to_string(),
                description: "Outputs ASCII ready for GPU glyph expansion".to_string(),
                code: "expand_glyphs(\"SOVEREIGN AI\")".to_string(),
                version: "1.0.0".to_string(),
                author: Some("system".to_string()),
                tags: vec!["gpu".to_string(), "glyphs".to_string()],
            },
        ];

        for cartridge in defaults {
            self.save_cartridge(&cartridge)?;
            self.cartridges.insert(cartridge.id.clone(), cartridge);
        }

        Ok(())
    }

    fn save_cartridge(&self, cartridge: &Cartridge) -> Result<(), CartridgeError> {
        let path = self
            .storage_root
            .join(format!("{}.json", cartridge.id));
        let content = serde_json::to_string_pretty(cartridge)?;
        fs::write(path, content)?;
        Ok(())
    }
}
