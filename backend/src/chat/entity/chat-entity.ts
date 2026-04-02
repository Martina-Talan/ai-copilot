import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  CreateDateColumn,
} from 'typeorm';

@Entity()
export class Chat {
  @PrimaryGeneratedColumn()
  id: number;

  @Column()
  documentId: string;

  @Column()
  userId: string;

  @Column()
  role: 'user' | 'assistant';

  @Column('text')
  content: string;

  @CreateDateColumn()
  createdAt: Date;
}
