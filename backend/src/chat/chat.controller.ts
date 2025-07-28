import { Body, Controller, Get, Param, Post } from '@nestjs/common';
import { ChatService } from './chat.service';
import { ChatDto } from './dto/chat.dto';

@Controller('chat')
export class ChatController {
  constructor(private readonly chatService: ChatService) {}

  @Post()
  async askQuestion(@Body() dto: ChatDto) {
    const { documentId, question } = dto;

    const response = await this.chatService.askQuestion(documentId, question);

    return response;
  }

  @Get(':documentId')
  async getChatHistory(@Param('documentId') documentId: number) {
    return this.chatService.getChatHistory(Number(documentId));
  }
}
