import { Router } from 'express';
import { generateEmbeddings } from '../app/vector/generateEmbeddings';

const router = Router();

router.post('/generate-embeddings', generateEmbeddings);

export default router;
