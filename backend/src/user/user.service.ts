import {
  Injectable,
  InternalServerErrorException,
  Logger,
} from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { User } from './entity/user.entity';

@Injectable()
export class UserService {
  private readonly logger = new Logger(UserService.name);

  constructor(
    @InjectRepository(User)
    private readonly userRepo: Repository<User>,
  ) {}

  async findAll(): Promise<User[]> {
    try {
      return await this.userRepo.find();
    } catch (error) {
      this.logger.error('Error fetching all users', error.stack);
      throw new InternalServerErrorException('Could not retrieve users');
    }
  }

  async findByEmail(email: string): Promise<User | null> {
    try {
      return await this.userRepo.findOne({ where: { email } });
    } catch (error) {
      this.logger.error(`Error finding user by email: ${email}`, error.stack);
      throw new InternalServerErrorException('Could not fetch user');
    }
  }

  async deleteAll(): Promise<void> {
    try {
      await this.userRepo.clear();
    } catch (error) {
      this.logger.error('Error deleting all users', error.stack);
      throw new InternalServerErrorException('Could not delete users');
    }
  }
}
