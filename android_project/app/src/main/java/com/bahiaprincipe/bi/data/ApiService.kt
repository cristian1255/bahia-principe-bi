package com.bahiaprincipe.bi.data

import com.bahiaprincipe.bi.data.model.AiConsultRequest
import com.bahiaprincipe.bi.data.model.AiConsultResponse
import com.bahiaprincipe.bi.data.model.KpiData
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

interface ApiService {
    @GET("api/v1/kpis")
    suspend fun getKpiSummary(@Query("region") region: String? = null): Response<List<KpiData>>

    @GET("kpis/details")
    suspend fun getKpiDetails(@Query("id") kpiId: String): Response<KpiData>

    @POST("api/v1/ai/consult")
    suspend fun consultAi(@Body request: AiConsultRequest): Response<AiConsultResponse>
}
