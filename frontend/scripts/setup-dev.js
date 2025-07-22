#!/usr/bin/env node

/**
 * Development environment setup script
 * This script sets up the development environment for the React frontend
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

console.log('🚀 Setting up React development environment...\n');

// Check if Node.js version is compatible
const nodeVersion = process.version;
const majorVersion = parseInt(nodeVersion.slice(1).split('.')[0]);

if (majorVersion < 16) {
  console.error('❌ Node.js version 16 or higher is required');
  console.error(`   Current version: ${nodeVersion}`);
  process.exit(1);
}

console.log(`✅ Node.js version: ${nodeVersion}`);

// Check if .env file exists, create from example if not
const envPath = path.join(__dirname, '..', '.env');
const envExamplePath = path.join(__dirname, '..', '.env.example');

if (!fs.existsSync(envPath)) {
  if (fs.existsSync(envExamplePath)) {
    fs.copyFileSync(envExamplePath, envPath);
    console.log('✅ Created .env file from .env.example');
  } else {
    console.log('⚠️  No .env.example file found, creating basic .env');
    fs.writeFileSync(envPath, `# React App Environment Variables
REACT_APP_API_BASE_URL=http://localhost:8000/api
REACT_APP_WS_BASE_URL=ws://localhost:8000/ws
`);
  }
} else {
  console.log('✅ .env file already exists');
}

// Install dependencies if node_modules doesn't exist
const nodeModulesPath = path.join(__dirname, '..', 'node_modules');
if (!fs.existsSync(nodeModulesPath)) {
  console.log('📦 Installing dependencies...');
  try {
    execSync('npm install', { 
      cwd: path.join(__dirname, '..'),
      stdio: 'inherit' 
    });
    console.log('✅ Dependencies installed successfully');
  } catch (error) {
    console.error('❌ Failed to install dependencies');
    console.error(error.message);
    process.exit(1);
  }
} else {
  console.log('✅ Dependencies already installed');
}

// Check TypeScript configuration
const tsconfigPath = path.join(__dirname, '..', 'tsconfig.json');
if (fs.existsSync(tsconfigPath)) {
  console.log('✅ TypeScript configuration found');
  
  // Run type check
  try {
    execSync('npm run type-check', { 
      cwd: path.join(__dirname, '..'),
      stdio: 'pipe' 
    });
    console.log('✅ TypeScript type check passed');
  } catch (error) {
    console.log('⚠️  TypeScript type check failed - this is normal during development');
  }
} else {
  console.error('❌ TypeScript configuration not found');
}

// Check ESLint configuration
const eslintPath = path.join(__dirname, '..', '.eslintrc.js');
if (fs.existsSync(eslintPath)) {
  console.log('✅ ESLint configuration found');
} else {
  console.log('⚠️  ESLint configuration not found');
}

// Check Prettier configuration
const prettierPath = path.join(__dirname, '..', '.prettierrc');
if (fs.existsSync(prettierPath)) {
  console.log('✅ Prettier configuration found');
} else {
  console.log('⚠️  Prettier configuration not found');
}

// Create necessary directories
const directories = [
  'src/components',
  'src/pages',
  'src/hooks',
  'src/store',
  'src/types',
  'src/utils',
  'src/services',
  'public'
];

directories.forEach(dir => {
  const dirPath = path.join(__dirname, '..', dir);
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
    console.log(`✅ Created directory: ${dir}`);
  }
});

console.log('\n🎉 Development environment setup complete!');
console.log('\nNext steps:');
console.log('1. Review and update .env file with your configuration');
console.log('2. Run "npm start" to start the development server');
console.log('3. Run "npm run lint" to check code quality');
console.log('4. Run "npm run format" to format code with Prettier');
console.log('5. Run "npm test" to run tests');

console.log('\n📚 Available scripts:');
console.log('  npm start          - Start development server');
console.log('  npm run build      - Build for production');
console.log('  npm test           - Run tests');
console.log('  npm run lint       - Run ESLint');
console.log('  npm run lint:fix   - Fix ESLint issues');
console.log('  npm run format     - Format code with Prettier');
console.log('  npm run type-check - Run TypeScript type checking');