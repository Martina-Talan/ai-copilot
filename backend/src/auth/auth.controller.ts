import {
  Controller,
  Post,
  Body,
  Logger,
  BadRequestException,
  UnauthorizedException,
  InternalServerErrorException,
} from '@nestjs/common';
import { AuthService } from './auth.service';
import { CreateUserDto } from './dto/create-user.dto';
import { LoginDto } from './dto/login.dto';
import { ApiTags, ApiResponse } from '@nestjs/swagger';

@ApiTags('auth')
@Controller('auth')
export class AuthController {
  private readonly logger = new Logger(AuthController.name);

  constructor(private readonly authService: AuthService) {}

  @Post('register')
  @ApiResponse({ status: 201, description: 'User registered' })
  async register(@Body() createUserDto: CreateUserDto) {
    const { email, password, username } = createUserDto;
    try {
      const result = await this.authService.register(email, password, username);
      return result;
    } catch (error) {
      this.logger.error(`Registration failed for ${email}`, error.stack);

      if (error instanceof BadRequestException) {
        throw error;
      }

      if (error.message?.toLowerCase().includes('exists')) {
        throw new BadRequestException('Email is already in use');
      }

      throw new InternalServerErrorException(
        'Registration failed due to a server error',
      );
    }
  }

  @Post('login')
  @ApiResponse({ status: 200, description: 'User logged in' })
  async login(@Body() loginDto: LoginDto) {
    const { email } = loginDto;
    try {
      const result = await this.authService.login(email, loginDto.password);
      return result;
    } catch (error) {
      this.logger.warn(`Login failed for ${email}`, error.stack);

      if (error instanceof UnauthorizedException) {
        throw new UnauthorizedException('Invalid email or password');
      }

      throw new InternalServerErrorException(
        'Login failed due to a server error',
      );
    }
  }
}
