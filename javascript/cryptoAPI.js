const express = require('express');
const app = express();
const port = 3000; // Choose any available port
app.use(express.json());

// Existing imports
const { Connection, PublicKey, Keypair, Transaction, ComputeBudgetProgram } = require('@solana/web3.js');
const { Liquidity } = require('@raydium-io/raydium-sdk');
const { getAssociatedTokenAddress, createAssociatedTokenAccountInstruction } = require('@solana/spl-token');
const bs58 = require('bs58');
const axios = require('axios');

// Solana & Wallet setup
const HELIUS_RPC = "https://api.devnet.solana.com";
const WALLET_PRIVATE_KEY = 'QdzhSjgSD67kYRmjCHUDb5hbRUtRLWJ3vHC4oU2AiAEdaT59h7hk2awVXXyqY2eFB3tm3XgjC9QSZC314Si3PDG';
const connection = new Connection(HELIUS_RPC, 'confirmed');
const privateKeyBytes = bs58.default.decode(WALLET_PRIVATE_KEY);
const wallet = Keypair.fromSecretKey(privateKeyBytes);
const SOL_MINT = new PublicKey('So11111111111111111111111111111111111111112');

// API Endpoints

// Get Balance
app.get('/balance', async (req, res) => {
    const balance = await connection.getBalance(wallet.publicKey);
    res.json({ balance: balance / 1e9 });
});

// Airdrop SOL
app.post('/airdrop', async (req, res) => {
    const { amount } = req.body;
    try {
        const lamports = amount * 1_000_000_000;
        const signature = await connection.requestAirdrop(wallet.publicKey, lamports);
        await connection.confirmTransaction(signature, 'confirmed');
        const balance = await connection.getBalance(wallet.publicKey);
        res.json({ message: `Airdrop successful`, tx: signature, newBalance: balance / 1e9 });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Buy Token
app.post('/buy', async (req, res) => {
    const { tokenMint, amount } = req.body;
    // Call buyToken logic here...
    res.json({ message: `Bought ${amount} SOL worth of ${tokenMint}` });
});

// Sell Token
app.post('/sell', async (req, res) => {
    const { tokenMint, amount } = req.body;
    // Call sellToken logic here...
    res.json({ message: `Sold ${amount} of ${tokenMint} for SOL` });
});

// Get Token Price
app.get('/price/:tokenMint', async (req, res) => {
    const tokenMint = req.params.tokenMint;
    try {
        const response = await axios.get(`https://api.jup.ag/price/v2?ids=${tokenMint}&vs_token=So11111111111111111111111111111111111111112`);
        const price = response.data.data[tokenMint]?.price;
        if (!price) throw new Error('Price not found');
        res.json({ token: tokenMint, price });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Start server
app.listen(port, () => {
    console.log(`Crypto bot API running on http://localhost:${port}`);
});
