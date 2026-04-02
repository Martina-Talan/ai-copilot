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

  constructor(@InjectRepository(Chat) private chatRepo: Repository<Chat>) {}

  async askQuestion(
    documentId: string,
    question: string,
    userId: string | number,
  ): Promise<ApiResponse> {
    const uid = String(userId);
    await this.chatRepo.save({
      userId: uid,
      documentId,
      role: 'user',
      content: question,
    });

    try {
      const { data } = await axios.post(
        'http://python-rag-service:8000/api/ask-question',
        {
          documentId: documentId.toString(),
          question,
        },
      );

      const answer =
        data?.answer?.contextAntwort || data?.answer?.text || 'No answer';
      await this.chatRepo.save({
        userId: uid,
        documentId,
        role: 'assistant',
        content: answer,
      });

      return data as ApiResponse;
    } catch (error: any) {
      const message = error?.response?.data || error.message;
      this.logger.error('Failed to get answer from AI service', message);
      throw new InternalServerErrorException(
        'AI-Service currently not available',
      );
    }
  }

  async getChatHistory(
    documentId: string,
    userId: string | number,
  ): Promise<Chat[]> {
    const uid = String(userId);
    try {
      return await this.chatRepo.find({
        where: { documentId, userId: uid },
        order: { createdAt: 'ASC' },
      });
    } catch (error) {
      this.logger.error(
        `Failed to load chat history for documentId=${documentId}, userId=${uid}`,
        error.stack,
      );
      throw new InternalServerErrorException('Could not fetch chat history');
    }
  }

  async clearChatHistory(
    documentId: string,
    userId: string | number,
  ): Promise<{ deleted: number }> {
    const uid = String(userId);
    try {
      const result = await this.chatRepo
        .createQueryBuilder()
        .delete()
        .from(Chat)
        .where('documentId = :documentId AND userId = :userId', {
          documentId,
          userId: uid,
        })
        .execute();

      return { deleted: result.affected ?? 0 };
    } catch (error) {
      this.logger.error(
        `Failed to clear chat history for documentId=${documentId}, userId=${uid}`,
        (error as Error).stack,
      );
      throw new InternalServerErrorException('Could not clear chat history');
    }
  }
}
