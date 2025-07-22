import express from 'express';
import cors from 'cors';
import bodyParser from 'body-parser';
import dotenv from 'dotenv';
import path from 'path';
import vectorRoutes from './api/vector.routes';
import pdfRoutes from './api/pdf.routes';

dotenv.config();

const app = express();

app.use(cors({ origin: 'http://localhost:5173', credentials: true }));
app.use(bodyParser.json());
app.use('/uploads', express.static(path.join(__dirname, '../uploads')));

app.use(vectorRoutes);
app.use(pdfRoutes);

export default app;
