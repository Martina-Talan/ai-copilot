import {
  Injectable,
  InternalServerErrorException,
  Logger,
} from '@nestjs/common';
import axios from 'axios';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Chat } from './entity/chat-entity';
import { ApiResponse } from 'src/types';

@Injectable()
export class ChatService {
  private readonly logger = new Logger(ChatService.name);

  constructor(
    @InjectRepository(Chat)
    private chatRepo: Repository<Chat>,
  ) {}

  async askQuestion(
    documentId: number,
    question: string,
  ): Promise<ApiResponse> {
    await this.chatRepo.save({ documentId, role: 'user', content: question });

    try {
      const response = await axios.post(
        'http://python-rag-service:8000/api/ask-question',
        {
          documentId: documentId.toString(),
          question,
        },
      );

      const answer = response.data?.answer?.kontextAntwort || 'No answer';

      await this.chatRepo.save({
        documentId,
        role: 'assistant',
        content: answer,
      });

      return response.data as ApiResponse;
    } catch (error: any) {
      const message = error?.response?.data || error.message;
      this.logger.error('Failed to get answer from AI service', message);
      throw new InternalServerErrorException(
        'AI-Service currently not available',
      );
    }
  }

  async getChatHistory(documentId: number): Promise<Chat[]> {
    try {
      return await this.chatRepo.find({
        where: { documentId },
        order: { createdAt: 'ASC' },
      });
    } catch (error) {
      this.logger.error(
        `Failed to load chat history for documentId=${documentId}`,
        error.stack,
      );
      throw new InternalServerErrorException('Could not fetch chat history');
    }
  }
}
