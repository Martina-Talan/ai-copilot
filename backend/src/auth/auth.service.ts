import {
  BadRequestException,
  Injectable,
  UnauthorizedException,
  Logger,
} from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import * as bcrypt from 'bcrypt';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { User } from '../user/entity/user.entity';

@Injectable()
export class AuthService {
  private readonly logger = new Logger(AuthService.name);

  constructor(
    private readonly jwtService: JwtService,
    @InjectRepository(User)
    private usersRepo: Repository<User>,
  ) {}

  async register(email: string, password: string, username: string) {
    try {
      const existing = await this.usersRepo.findOne({
        where: [{ email }, { username }],
      });
      if (existing) {
        this.logger.warn(
          `Registration failed: Email or username already in use (${email})`,
        );
        throw new UnauthorizedException('Email or username already in use');
      }

      if (!password) {
        this.logger.warn(
          `Registration failed: No password provided for ${email}`,
        );
        throw new BadRequestException('Password is required');
      }

      const hash = await bcrypt.hash(password, 10);
      const user: Partial<User> = {
        email,
        username,
        password: hash,
      };

      const newUser = this.usersRepo.create(user);
      const savedUser = await this.usersRepo.save(newUser);

      return {
        message: 'User successfully registered',
        user: { id: savedUser.id, email: savedUser.email },
        username: savedUser.username,
      };
    } catch (error) {
      this.logger.error(`Registration error for ${email}`, error.stack);
      throw error;
    }
  }

  async login(email: string, password: string) {
    try {
      const user = await this.usersRepo.findOne({ where: { email } });
      if (!user) {
        this.logger.warn(`Login failed: User not found (${email})`);
        throw new UnauthorizedException('Invalid credentials');
      }

      const valid = await bcrypt.compare(password, user.password);
      if (!valid) {
        this.logger.warn(`Login failed: Incorrect password for ${email}`);
        throw new UnauthorizedException('Invalid credentials');
      }

      const payload = {
        sub: user.id,
        email: user.email,
        username: user.username,
      };
      const token = this.jwtService.sign(payload);

      return { access_token: token };
    } catch (error) {
      this.logger.error(`Login error for ${email}`, error.stack);
      throw error;
    }
  }
}
