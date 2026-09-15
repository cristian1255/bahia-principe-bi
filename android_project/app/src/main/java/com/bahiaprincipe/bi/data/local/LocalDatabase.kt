package com.bahiaprincipe.bi.data.local

import android.content.Context
import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Entity(tableName = "kpis")
data class KpiEntity(
    @PrimaryKey val title: String,
    val value: String,
    val trend: String,
    val isPositiveTrend: Boolean,
    val colorHex: String
)

@Entity(tableName = "users")
data class UserEntity(
    @PrimaryKey val email: String,
    val name: String,
    val role: String,
    val password: String // En un entorno real esto iría encriptado o vía OAuth
)

@Entity(tableName = "generated_reports")
data class GeneratedReportEntity(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val title: String,
    val date: String,
    val filePath: String,
    val type: String // "MANUAL" o "SEMANAL"
)

@Entity(tableName = "chat_messages")
data class ChatMessageEntity(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val content: String,
    val isUser: Boolean,
    val timestamp: Long = System.currentTimeMillis()
)

@Dao
interface ExecutiveDao {
    @Query("SELECT * FROM kpis")
    fun getAllKpis(): Flow<List<KpiEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertKpis(kpis: List<KpiEntity>)

    @Query("SELECT * FROM users WHERE email = :email LIMIT 1")
    suspend fun getUser(email: String): UserEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertUser(user: UserEntity)

    @Query("SELECT * FROM generated_reports ORDER BY id DESC")
    fun getAllReports(): Flow<List<GeneratedReportEntity>>

    @Insert
    suspend fun insertReport(report: GeneratedReportEntity)

    @Query("SELECT * FROM chat_messages ORDER BY timestamp ASC")
    fun getAllChatMessages(): Flow<List<ChatMessageEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertChatMessage(message: ChatMessageEntity)

    @Query("DELETE FROM chat_messages")
    suspend fun clearChatMessages()
}

@Database(entities = [KpiEntity::class, UserEntity::class, GeneratedReportEntity::class, ChatMessageEntity::class], version = 3, exportSchema = false)
abstract class LocalDatabase : RoomDatabase() {
    abstract fun executiveDao(): ExecutiveDao

    companion object {
        @Volatile
        private var INSTANCE: LocalDatabase? = null

        fun getDatabase(context: Context): LocalDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    LocalDatabase::class.java,
                    "bahia_bi_db"
                ).fallbackToDestructiveMigration().build()
                INSTANCE = instance
                instance
            }
        }
    }
}
