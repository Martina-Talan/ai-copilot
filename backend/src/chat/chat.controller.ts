import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  Post,
  Req,
  UseGuards,
} from '@nestjs/common';
import { ChatService } from './chat.service';
import { ChatDto } from './dto/chat.dto';
import { AuthGuard } from '@nestjs/passport';

@Controller('chat')
@UseGuards(AuthGuard('jwt'))
export class ChatController {
  constructor(private readonly chatService: ChatService) {}

  @Post()
  async askQuestion(@Body() dto: ChatDto, @Req() req) {
    const userId = req.user?.id;
    return this.chatService.askQuestion(dto.documentId, dto.question, userId);
  }

  @Get(':documentId')
  async getChatHistory(@Param('documentId') documentId: string, @Req() req) {
    const userId = req.user?.id;
    return this.chatService.getChatHistory(String(documentId), userId);
  }

  @Delete(':documentId')
  async clear(@Param('documentId') documentId: string, @Req() req) {
    const userId = String(req.user?.id);
    await this.chatService.clearChatHistory(documentId, userId);
    return { ok: true };
  }
}
