import { IsString, IsNumber } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';
import { Type } from 'class-transformer';

export class ChatDto {
  @ApiProperty()
  @IsNumber()
  @Type(() => Number)
  documentId: number;

  @ApiProperty()
  @IsString()
  question: string;
}
